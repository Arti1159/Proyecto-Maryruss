import hashlib
import io
import json
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .backup import create_backup, validate_backup
from .forms import GarmentForm
from .models import Collection, Garment, BudgetLine, Expense, ProductionEvent, Audit
from .services import summarize, approve_budget, record_event, record_expense, void_record, set_paid

class StudioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('owner', password='Test-only-strong-2026', is_staff=True)
        cls.operator = get_user_model().objects.create_user('operator', password='Test-only-strong-2026')
        cls.collection = Collection.objects.create(name='Prueba de producción', budget='1000')
        cls.model = Garment.objects.create(collection=cls.collection, code='BL-01', name='Blusa de prueba', planned_units=20)
        for category, label, quantity, unit_price, basis in [
            ('fabric', 'Tela', '1.2', '10', 'unit'), ('supplies', 'Botones', '4', '.5', 'unit'),
            ('sewing', 'Confección', '1', '8', 'unit'), ('packaging', 'Empaque', '1', '1', 'unit'),
            ('transport', 'Entrega fija', '1', '100', 'batch'),
        ]:
            BudgetLine.objects.create(garment=cls.model, category=category, description=label, quantity=quantity, unit_price=unit_price, basis=basis)

    def setUp(self):
        self.client.force_login(self.user)

    def approve(self):
        return approve_budget(self.model.pk, self.user)

    def event(self, stage, quantity, token=None):
        return record_event(self.model.pk, self.user, {'stage': stage, 'quantity': quantity, 'date': timezone.localdate(), 'notes': ''}, token or uuid.uuid4())

    def expense(self, amount='230', paid='100', token=None):
        return record_expense(self.model.pk, self.user, {'category': 'fabric', 'description': 'Consumo y servicios', 'amount': Decimal(amount), 'paid_amount': Decimal(paid), 'date': timezone.localdate(), 'supplier': 'Taller', 'reference': '', 'notes': ''}, token or uuid.uuid4())

    def test_unit_and_fixed_budget_exact_totals(self):
        s = summarize(self.model)
        self.assertEqual(s['planned'], Decimal('560.00'))
        self.assertEqual(s['planned_unit'], Decimal('28.00'))
        self.assertEqual(s['actual'], Decimal('0'))

    def test_currency_rounding_is_half_up(self):
        self.model.budget_lines.all().delete()
        BudgetLine.objects.create(garment=self.model, category='other', description='Ajuste', quantity=1, unit_price=Decimal('0.005'), basis='batch')
        self.assertEqual(summarize(self.model)['planned'], Decimal('0.01'))

    def test_approval_snapshot_preserves_old_prices_and_quantities(self):
        self.approve()
        line = self.model.budget_lines.get(category='fabric')
        line.unit_price = '20'
        line.save()
        self.model.refresh_from_db()
        s = summarize(self.model)
        self.assertEqual(s['baseline'], Decimal('560.00'))
        self.assertEqual(s['planned'], Decimal('800.00'))
        self.assertTrue(s['changed'])
        self.approve()
        self.model.refresh_from_db()
        self.assertEqual(self.model.approved_budget, Decimal('800.00'))
        approval = Audit.objects.filter(action='budget.approved').first()
        self.assertEqual(approval.details['previous']['total'], '560.00')

    def test_empty_budget_cannot_be_approved(self):
        self.model.budget_lines.all().delete()
        with self.assertRaises(ValidationError):
            self.approve()

    def test_approval_over_collection_budget_needs_explicit_override(self):
        self.collection.budget = '500'
        self.collection.save()
        with self.assertRaises(ValidationError):
            self.approve()
        self.model.refresh_from_db()
        self.assertIsNone(self.model.approved_budget)
        approve_budget(self.model.pk, self.user, allow_overbudget=True)
        self.model.refresh_from_db()
        self.assertEqual(self.model.approved_budget, Decimal('560.00'))

    def test_partial_production_does_not_duplicate_prendas(self):
        self.approve()
        for stage in ['cut', 'sewing', 'finishing']:
            self.event(stage, 10)
        self.event('approved', 8)
        self.event('rejected', 2)
        s = summarize(self.model)
        self.assertEqual(s['good'], 8)
        self.assertEqual(s['progress'], 40)
        self.assertEqual(sum(b['quantity'] for b in s['bands']), 20)
        self.assertEqual(s['counts']['cut'], 10)

    def test_production_requires_approved_plan(self):
        with self.assertRaises(ValidationError):
            self.event('cut', 1)

    def test_stages_cannot_exceed_preceding_stage_or_plan(self):
        self.approve()
        with self.assertRaises(ValidationError):
            self.event('sewing', 1)
        with self.assertRaises(ValidationError):
            self.event('cut', 21)
        self.event('cut', 10)
        self.event('sewing', 8)
        with self.assertRaises(ValidationError):
            self.event('finishing', 9)
        self.event('finishing', 8)
        self.event('approved', 6)
        with self.assertRaises(ValidationError):
            self.event('rejected', 3)

    def test_event_retry_has_only_one_effect(self):
        self.approve()
        token = uuid.uuid4()
        original, first = self.event('cut', 5, token)
        retry, second = self.event('cut', 5, token)
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(original.pk, retry.pk)
        self.assertEqual(summarize(self.model)['counts']['cut'], 5)

    def test_expense_retry_has_only_one_effect(self):
        token = uuid.uuid4()
        self.expense(token=token)
        _, created = self.expense(token=token)
        self.assertFalse(created)
        self.assertEqual(summarize(self.model)['actual'], Decimal('230.00'))
        self.assertEqual(Expense.objects.count(), 1)

    def test_actual_unit_denominators_are_explicit(self):
        self.approve()
        for stage in ['cut', 'sewing', 'finishing', 'approved']:
            self.event(stage, 10)
        self.expense('330', '100')
        s = summarize(self.model)
        self.assertEqual(s['actual_unit'], Decimal('16.50'))
        self.assertEqual(s['good_unit'], Decimal('33.00'))
        self.assertEqual(s['balance'], Decimal('230.00'))
        self.assertEqual(s['paid'], Decimal('100.00'))
        self.assertEqual(s['unpaid'], Decimal('230.00'))

    def test_no_good_units_returns_unavailable_cost(self):
        self.expense()
        self.assertIsNone(summarize(self.model)['good_unit'])

    def test_paid_total_updates_without_new_cost_and_rejects_excess(self):
        expense, _ = self.expense()
        set_paid(expense.pk, self.user, Decimal('200'))
        set_paid(expense.pk, self.user, Decimal('200'))
        self.assertEqual(summarize(self.model)['actual'], Decimal('230'))
        self.assertEqual(summarize(self.model)['paid'], Decimal('200'))
        self.assertEqual(Audit.objects.filter(action='payment.updated').count(), 1)
        with self.assertRaises(ValidationError):
            set_paid(expense.pk, self.user, Decimal('231'))

    def test_invalid_payment_cannot_create_expense(self):
        with self.assertRaises(ValidationError):
            self.expense('100', '101')
        self.assertEqual(Expense.objects.count(), 0)

    def test_void_preserves_original_and_excludes_totals(self):
        expense, _ = self.expense()
        void_record(Expense, expense.pk, self.user, 'Error de digitación')
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal('230'))
        self.assertTrue(expense.voided)
        self.assertEqual(summarize(self.model)['actual'], Decimal('0'))
        self.assertEqual(summarize(self.model)['paid'], Decimal('0'))

    def test_cannot_void_predecessor_used_by_later_stage(self):
        self.approve()
        cut, _ = self.event('cut', 10)
        self.event('sewing', 10)
        with self.assertRaises(ValidationError):
            void_record(ProductionEvent, cut.pk, self.user, 'Corrección')
        cut.refresh_from_db()
        self.assertFalse(cut.voided)

    def test_new_approved_plan_cannot_drop_below_cut_units(self):
        self.approve()
        self.event('cut', 10)
        self.model.planned_units = 5
        self.model.save()
        with self.assertRaises(ValidationError):
            self.approve()

    def test_archive_blocks_new_operaciones_but_keeps_costs(self):
        self.approve()
        self.expense()
        self.model.archived = True
        self.model.save()
        with self.assertRaises(ValidationError):
            self.event('cut', 1)
        with self.assertRaises(ValidationError):
            self.expense()
        self.assertEqual(summarize(self.model)['actual'], Decimal('230'))

    def test_deadline_alert_and_budget_excess(self):
        self.approve()
        self.model.due_date = timezone.localdate() - timedelta(days=1)
        self.model.save()
        self.expense('600', '0')
        s = summarize(self.model)
        self.assertTrue(s['overdue'])
        self.assertTrue(s['over_budget'])
        self.assertEqual(s['balance'], Decimal('-40'))

    def test_all_pages_render_with_populated_model(self):
        self.approve()
        self.event('cut', 5)
        expense, _ = self.expense()
        paths = ['/', '/colecciones/', f'/colecciones/{self.collection.pk}/', '/colecciones/nueva/',
                 '/modelos/', f'/modelos/{self.model.pk}/', '/modelos/nuevo/',
                 f'/modelos/{self.model.pk}/editar/', f'/modelos/{self.model.pk}/costos/nuevo/',
                 f'/avances/nuevo/?modelo={self.model.pk}', f'/gastos/nuevo/?modelo={self.model.pk}',
                 '/gastos/', f'/gastos/{expense.pk}/pago/', '/actividad/', '/guia/', '/cuenta/contrasena/']
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        response = self.client.get(f'/modelos/{self.model.pk}/')
        self.assertContains(response, 'S/ 560.00')
        self.assertContains(response, 'S/ 28.00')

    def test_empty_dashboard_and_lists_render(self):
        other = Collection.objects.create(name='Colección vacía', budget='0')
        self.assertEqual(self.client.get(f'/?collection={other.pk}').status_code, 200)
        self.assertEqual(self.client.get('/?collection=invalido').status_code, 200)
        self.assertEqual(self.client.get('/modelos/?status=done').status_code, 200)

    def test_http_expense_and_production_forms_persist_and_retry(self):
        self.approve()
        token = str(uuid.uuid4())
        values = {'garment': self.model.pk, 'stage': 'cut', 'quantity': '5', 'date': str(timezone.localdate()), 'notes': '', 'token': token}
        self.assertEqual(self.client.post('/avances/nuevo/', values).status_code, 302)
        self.assertEqual(self.client.post('/avances/nuevo/', values).status_code, 302)
        self.assertEqual(ProductionEvent.objects.count(), 1)
        values = {'garment': self.model.pk, 'category': 'fabric', 'description': 'Consumo', 'amount': '120', 'paid_amount': '50', 'date': str(timezone.localdate()), 'supplier': '', 'reference': '', 'notes': '', 'token': str(uuid.uuid4())}
        self.assertEqual(self.client.post('/gastos/nuevo/', values).status_code, 302)
        self.assertEqual(self.client.post('/gastos/nuevo/', values).status_code, 302)
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(summarize(Garment.objects.get(pk=self.model.pk))['actual'], Decimal('120'))

    def test_form_invalid_stage_shows_error_and_no_record(self):
        self.approve()
        response = self.client.post('/avances/nuevo/', {'garment': self.model.pk, 'stage': 'sewing', 'quantity': '1', 'date': str(timezone.localdate()), 'token': str(uuid.uuid4())})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No puedes confeccionar')
        self.assertEqual(ProductionEvent.objects.count(), 0)

    def test_future_operation_date_rejected(self):
        self.approve()
        response = self.client.post('/avances/nuevo/', {'garment': self.model.pk, 'stage': 'cut', 'quantity': '1', 'date': str(timezone.localdate() + timedelta(days=1)), 'token': str(uuid.uuid4())})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'hoy o anterior')
        self.assertEqual(ProductionEvent.objects.count(), 0)

    def test_anonymous_and_operator_permissions(self):
        self.client.logout()
        for path in ['/', '/modelos/', '/gastos/', '/exportar/modelos/', '/respaldo/']:
            self.assertEqual(self.client.get(path).status_code, 302)
        self.client.force_login(self.operator)
        for path in ['/colecciones/nueva/', '/modelos/nuevo/', f'/modelos/{self.model.pk}/costos/nuevo/', '/respaldo/']:
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.post(f'/modelos/{self.model.pk}/aprobar/').status_code, 403)
        self.assertEqual(self.client.get('/gastos/nuevo/').status_code, 200)

    def test_csrf_blocks_unauthorized_post_and_get_cannot_mutate(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(f'/modelos/{self.model.pk}/aprobar/').status_code, 403)
        self.assertEqual(self.client.get(f'/modelos/{self.model.pk}/aprobar/').status_code, 405)
        self.model.refresh_from_db()
        self.assertIsNone(self.model.approved_budget)

    def test_csv_export_has_amounts_and_injection_protection(self):
        self.model.name = '=malicious()'
        self.model.save()
        response = self.client.get('/exportar/modelos/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        self.assertIn("'=malicious()", content)
        self.assertIn('560.00', content)

    def test_model_unique_code_and_moving_operated_model_rejected(self):
        self.approve()
        other = Collection.objects.create(name='Otra', budget='1000')
        form = GarmentForm({'collection': other.pk, 'code': 'BL-01', 'name': 'Blusa', 'category': 'blouse', 'planned_units': '20'}, instance=self.model)
        self.assertFalse(form.is_valid())
        self.assertIn('collection', form.errors)

    def test_demo_seed_refuses_real_database(self):
        with override_settings(DEMO_MODE=False):
            with self.assertRaises(CommandError):
                call_command('seed_demo', stdout=io.StringIO())

    def test_demo_seed_refuses_database_with_real_users(self):
        with override_settings(DEMO_MODE=True):
            with self.assertRaises(CommandError):
                call_command('seed_demo', stdout=io.StringIO())
        self.assertFalse(get_user_model().objects.filter(username='demo').exists())

    def test_demo_login_unavailable_in_real_mode(self):
        with override_settings(DEMO_MODE=False):
            self.assertEqual(self.client.post('/demo/entrar/').status_code, 404)

    def test_budget_edit_keeps_approved_snapshot(self):
        self.approve()
        line = self.model.budget_lines.get(category='fabric')
        response = self.client.post(reverse('budget_edit', args=[self.model.pk, line.pk]), {'category': 'fabric', 'description': 'Tela nueva', 'basis': 'unit', 'quantity': '1.2', 'unit': 'm', 'unit_price': '20'})
        self.assertEqual(response.status_code, 302)
        self.model.refresh_from_db()
        self.assertEqual(self.model.approved_budget, Decimal('560'))
        self.assertTrue(summarize(self.model)['changed'])

class BackupTests(TransactionTestCase):
    def create_source(self, directory):
        # Use actual migrations in an isolated file, independent of the test runner's in-memory DB.
        path = Path(directory) / 'source.sqlite3'
        from django.db import connection
        with sqlite3.connect(path) as target:
            connection.connection.backup(target)
        return path

    def test_backup_validation_and_restore_preserve_data(self):
        with tempfile.TemporaryDirectory() as directory:
            Collection.objects.create(name='Persistente', budget='1234.56')
            path = self.create_source(directory)
            payload = create_backup(path)
            manifest, data = validate_backup(payload)
            self.assertEqual(manifest['format'], 'maryruss-backup')
            archive = Path(directory) / 'backup.zip'
            archive.write_bytes(payload)
            target = Path(directory) / 'restored.sqlite3'
            call_command('restore_backup', str(archive), target=str(target), confirm=True, stdout=io.StringIO())
            with sqlite3.connect(target) as db:
                self.assertEqual(db.execute('SELECT name FROM studio_collection').fetchone()[0], 'Persistente')
                self.assertEqual(Decimal(str(db.execute('SELECT budget FROM studio_collection').fetchone()[0])), Decimal('1234.56'))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM django_session').fetchone()[0], 0)

    def test_corrupted_hash_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = create_backup(self.create_source(directory))
            manifest, data = validate_backup(payload)
            manifest['sha256'] = 'incorrect'
            modified = io.BytesIO()
            with zipfile.ZipFile(modified, 'w') as output:
                output.writestr('manifest.json', json.dumps(manifest))
                output.writestr('database.sqlite3', data)
            with self.assertRaises(ValueError):
                validate_backup(modified.getvalue())

    def test_restore_requires_confirmation_and_fresh_target(self):
        with self.assertRaises(CommandError):
            call_command('restore_backup', 'unused.zip', stdout=io.StringIO())
