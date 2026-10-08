import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from .forms import BudgetLineForm, ExpenseCategoryForm, ExpenseForm
from .models import Audit, BudgetLine, Collection, Expense, ExpenseCategory, Garment
from .services import approve_budget, record_expense, set_paid, snapshot, summarize

class CategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('settings-owner', is_staff=True)
        cls.operator = get_user_model().objects.create_user('settings-operator')
        cls.collection = Collection.objects.create(name='Categorías', budget='10000')
        cls.garment = Garment.objects.create(collection=cls.collection, code='CAT', name='Prueba', planned_units=500)

    def setUp(self):
        self.client.force_login(self.user)

    def new_category(self):
        return ExpenseCategory.objects.create(name='Bordado', description='Logo y aplicaciones')

    def line(self, category):
        return BudgetLine.objects.create(garment=self.garment, category=category, description='Logo', quantity=1, unit_price=3)

    def expense(self, category):
        return record_expense(self.garment.pk, self.user, {'category': category, 'description': 'Logo', 'amount': Decimal('1500'), 'paid_amount': Decimal('300'), 'date': timezone.localdate()}, uuid.uuid4())[0]

    def test_create_trim_unique_category_and_audit(self):
        response = self.client.post(reverse('category_create'), {'name':'  Bordado   especial  ', 'description':'Logo'})
        self.assertRedirects(response, reverse('settings'))
        category = ExpenseCategory.objects.get(name='Bordado especial')
        self.assertTrue(category.active)
        self.assertTrue(Audit.objects.filter(action='category.saved', details__code=category.pk).exists())
        for name in ['bordado especial', '  BORDADO    ESPECIAL ', ' ']:
            self.assertFalse(ExpenseCategoryForm({'name':name}).is_valid())
        category.active = False
        category.save()
        self.assertFalse(ExpenseCategoryForm({'name':'Bordado especial'}).is_valid())
        self.assertFalse(ExpenseCategoryForm({'name':'CONFECCIÓN'}).is_valid())

    def test_custom_category_integrates_plan_expenses_charts_filters_csv(self):
        category = self.new_category()
        line = self.line(category)
        self.expense(category)
        self.assertEqual(snapshot(self.garment)['lines'][0]['category'], category.pk)
        self.assertEqual(summarize(self.garment)['planned'], Decimal('1500.00'))
        for url in [reverse('dashboard'), reverse('garment_detail', args=[self.garment.pk]), reverse('expense_list')+'?category='+category.pk, reverse('export', args=['gastos'])]:
            self.assertContains(self.client.get(url), 'Bordado')
        filtered = self.client.get(reverse('expense_list')+'?category=fabric')
        self.assertEqual(filtered.context['amount'], 0)
        self.assertEqual(line.get_category_display(), 'Bordado')

    def test_archive_preserves_old_records_and_payment_but_blocks_new_costs(self):
        category = self.new_category()
        line = self.line(category)
        expense = self.expense(category)
        approve_budget(self.garment.pk, self.user)
        saved_snapshot = Garment.objects.get(pk=self.garment.pk).approved_snapshot
        response = self.client.post(reverse('category_status', args=[category.pk]), {'active':'0'})
        self.assertRedirects(response, reverse('settings'))
        category.refresh_from_db()
        self.assertFalse(category.active)
        self.assertNotIn(category, BudgetLineForm(instance=BudgetLine(garment=self.garment)).fields['category'].queryset)
        self.assertNotIn(category, ExpenseForm().fields['category'].queryset)
        self.assertIn(category, BudgetLineForm(instance=line).fields['category'].queryset)
        line.full_clean()  # Editing the existing record remains supported.
        set_paid(expense.pk, self.user, Decimal('600'))
        expense.refresh_from_db()
        self.assertEqual(expense.paid_amount, Decimal('600'))
        with self.assertRaises(ValidationError):
            self.expense(category)
        new = BudgetLine(garment=self.garment, category=category, description='Nuevo', quantity=1, unit_price=5)
        with self.assertRaises(ValidationError):
            new.full_clean()
        self.garment.refresh_from_db()
        self.assertEqual(self.garment.approved_snapshot, saved_snapshot)
        self.assertFalse(summarize(self.garment)['changed'])
        for url in [reverse('dashboard'), reverse('expense_list')+'?category='+category.pk]:
            self.assertContains(self.client.get(url), 'Bordado')

    def test_archived_category_cannot_be_chosen_via_forged_post(self):
        category = self.new_category()
        category.active = False
        category.save()
        before = BudgetLine.objects.count()
        response = self.client.post(reverse('budget_create', args=[self.garment.pk]), {'category':category.pk,'description':'Nuevo','basis':'unit','quantity':'1','unit':'prenda','unit_price':'3'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('category', response.context['form'].errors)
        self.assertEqual(BudgetLine.objects.count(), before)

    def test_rename_preserves_approved_version_and_totals(self):
        category = self.new_category()
        self.line(category)
        approve_budget(self.garment.pk, self.user)
        before = Garment.objects.get(pk=self.garment.pk).approved_snapshot
        response = self.client.post(reverse('category_edit', args=[category.pk]), {'name':'Aplicaciones', 'description':'Nueva descripción'})
        self.assertRedirects(response, reverse('settings'))
        self.garment.refresh_from_db()
        self.assertEqual(self.garment.approved_snapshot, before)
        self.assertFalse(summarize(self.garment)['changed'])
        self.assertContains(self.client.get(reverse('garment_detail', args=[self.garment.pk])), 'Aplicaciones')
        self.assertEqual(Audit.objects.filter(action='category.saved').first().details['previous']['name'], 'Bordado')

    def test_reactivate_and_duplicate_status_requests_are_idempotent(self):
        category = self.new_category()
        for state in ['0','0','1','1']:
            self.client.post(reverse('category_status', args=[category.pk]), {'active':state})
            category.refresh_from_db()
            self.assertEqual(category.active, state == '1')
        self.assertIn(category, ExpenseForm().fields['category'].queryset)
        self.assertEqual(self.client.get(reverse('category_status', args=[category.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse('category_status', args=[category.pk]), {'active':'invalid'}).status_code, 400)

    def test_category_operations_require_admin_and_login(self):
        category = self.new_category()
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse('settings')).status_code, 200)
        for name, args in [('category_create', []), ('category_edit',[category.pk]), ('category_status',[category.pk])]:
            self.assertEqual(self.client.post(reverse(name, args=args), {'active':'0','name':'Nuevo'}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('category_options')).status_code, 302)
        self.assertEqual(self.client.get(reverse('settings')).status_code, 302)

    def test_options_are_dynamic_and_exclude_archived_categories(self):
        category = self.new_category()
        response = self.client.get(reverse('category_options'))
        self.assertIn({'code':category.pk,'name':'Bordado','description':'Logo y aplicaciones'}, response.json()['categories'])
        category.active = False
        category.save()
        self.assertNotIn(category.pk, [x['code'] for x in self.client.get(reverse('category_options')).json()['categories']])

    def test_all_budget_fields_have_accessible_guidance(self):
        form = BudgetLineForm(instance=BudgetLine(garment=self.garment))
        for name, field in form.fields.items():
            self.assertTrue(field.help_text)
            self.assertTrue(field.info_text)
            self.assertEqual(field.widget.attrs['aria-describedby'], f'id_{name}_help')
        self.assertContains(self.client.get(reverse('budget_create', args=[self.garment.pk])), 'Estás preparando un presupuesto para 500 prendas')

class CategoryMigrationTests(TransactionTestCase):
    def test_legacy_migration_preserves_approved_snapshot_amounts_payments_and_unknown_codes(self):
        old = [('studio', '0001_initial')]
        latest = [('studio', '0002_expensecategory_alter_budgetline_category_and_more')]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            user = get_user_model().objects.create(username='legacy')
            collection = apps.get_model('studio','Collection').objects.create(name='Existente', budget='10000')
            garment = apps.get_model('studio','Garment').objects.create(collection=collection, code='V1', name='Prueba', planned_units=500)
            Line = apps.get_model('studio','BudgetLine')
            line = Line.objects.create(garment=garment, category='fabric', description='Tela', basis='unit', quantity='1.2', unit='m', unit_price='10')
            unknown = Line.objects.create(garment=garment, category='legacy_extra', description='Importado', basis='batch', quantity='1', unit='servicio', unit_price='80')
            lines = list(Line.objects.filter(garment=garment))
            approved = {'units':500, 'lines':[{'id':l.pk,'category':l.category,'description':l.description,'basis':l.basis,'quantity':str(l.quantity),'unit':l.unit,'unit_price':str(l.unit_price)} for l in lines], 'total':'6080.00'}
            garment.approved_snapshot = approved
            garment.approved_budget = Decimal('6080')
            garment.approved_units = 500
            garment.save()
            expense = apps.get_model('studio','Expense').objects.create(garment=garment, category='fabric', description='Tela', amount='400', paid_amount='125', created_by_id=user.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            upgraded = Garment.objects.get(pk=garment.pk)
            self.assertEqual(upgraded.approved_snapshot, approved)
            self.assertEqual(BudgetLine.objects.get(pk=line.pk).category_id, 'fabric')
            self.assertEqual(BudgetLine.objects.get(pk=unknown.pk).get_category_display(), 'Importada: legacy_extra')
            self.assertEqual(Expense.objects.get(pk=expense.pk).paid_amount, Decimal('125.00'))
            summary = summarize(upgraded)
            self.assertEqual(summary['planned'], Decimal('6080.00'))
            self.assertEqual(summary['actual'], Decimal('400.00'))
            self.assertFalse(summary['changed'])
            self.assertEqual(connection.cursor().execute('PRAGMA foreign_key_check').fetchall(), [])
        finally:
            MigrationExecutor(connection).migrate(latest)
