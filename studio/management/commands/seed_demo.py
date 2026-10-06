import uuid
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from studio.models import Collection, Garment, BudgetLine, Audit
from studio.services import approve_budget, record_event, record_expense

class Command(BaseCommand):
    help = 'Carga datos ficticios una sola vez y solo cuando MARYRUSS_DEMO=1.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError('Protección activa: seed_demo solo funciona con MARYRUSS_DEMO=1 y una base de prueba separada.')
        User = get_user_model()
        if User.objects.exclude(username='demo').exists():
            raise CommandError('La base contiene usuarios ajenos a la demostración. No se añadirán datos ficticios.')
        if Collection.objects.exists() or Garment.objects.exists():
            self.stdout.write('La demostración ya tiene datos. No se modificó ni duplicó ningún registro.')
            return
        user, created = User.objects.get_or_create(username='demo', defaults={'is_staff': True, 'is_superuser': True, 'first_name': 'Demo'})
        if created:
            user.set_unusable_password()
            user.save()
        today = timezone.localdate()
        first = Collection.objects.create(name='Esenciales de primavera', season='Primavera · 2026', budget='16000', due_date=today + timedelta(days=22), notes='DATOS FICTICIOS. Colección de ejemplo para explorar cantidades, costos y avances.')
        second = Collection.objects.create(name='Cápsula de fin de semana', season='Edición limitada · 2026', budget='6800', due_date=today + timedelta(days=35), notes='DATOS FICTICIOS. No constituye una recomendación de producción ni de precios.')
        specs = [
            (first, 'BL-001', 'Blusa Aurora', 'blouse', 80, 'Crudo · arena', 'S 20 · M 40 · L 20', 'Taller Rosas', 1.2, 14, 12, 60, 45, 30, 24, 0, 0),
            (first, 'PT-002', 'Pantalón Lino', 'pants', 60, 'Oliva · natural', 'S 15 · M 30 · L 15', 'Taller Central', 1.6, 18, 18, 40, 30, 18, 12, 2, 0),
            (first, 'VT-003', 'Vestido Brisa', 'dress', 40, 'Terracota', 'S 10 · M 20 · L 10', 'Taller Rosas', 2.1, 16, 22, 40, 35, 28, 20, 1, -2),
            (second, 'CM-004', 'Camisa Domingo', 'shirt', 50, 'Marfil · celeste', 'S 10 · M 25 · L 15', 'Taller Norte', 1.5, 13, 15, 50, 50, 50, 48, 2, 12),
            (second, 'CS-005', 'Casaca Nube', 'jacket', 30, 'Verde salvia', 'S 5 · M 15 · L 10', 'Taller Central', 1.8, 22, 27, 0, 0, 0, 0, 0, 25),
        ]
        for collection, code, name, category, units, color, sizes, workshop, consumption, price, sewing, cut, sewn, finishing, good, rejects, deadline in specs:
            model = Garment.objects.create(collection=collection, code=code, name=name, category=category, planned_units=units, color=color, sizes=sizes, workshop=workshop, due_date=today + timedelta(days=deadline or 14), notes='DATOS FICTICIOS. Consumo y precios de demostración; no son mediciones del taller.')
            for kind, label, basis, quantity, unit, unit_price in [
                ('fabric', 'Tela principal', 'unit', str(consumption), 'm', str(price)),
                ('supplies', 'Botones y etiquetas', 'unit', '1', 'juego', '3.50'),
                ('cut', 'Servicio de corte', 'unit', '1', 'prenda', '2.50'),
                ('sewing', 'Confección', 'unit', '1', 'prenda', str(sewing)),
                ('finishing', 'Acabados y revisión', 'unit', '1', 'prenda', '3.00'),
                ('packaging', 'Empaque', 'unit', '1', 'prenda', '1.00'),
                ('transport', 'Entrega del lote', 'batch', '1', 'servicio', '100.00'),
            ]:
                BudgetLine.objects.create(garment=model, category=kind, description=label, basis=basis, quantity=quantity, unit=unit, unit_price=unit_price)
            approve_budget(model.pk, user)
            for kind, number in [('cut', cut), ('sewing', sewn), ('finishing', finishing), ('approved', good), ('rejected', rejects)]:
                if number:
                    record_event(model.pk, user, {'stage': kind, 'quantity': number, 'date': today - timedelta(days=2), 'notes': 'Avance ficticio de demostración.'}, uuid.uuid4())
            if cut:
                amounts = [
                    ('fabric', 'Tela consumida en el lote', Decimal(str(consumption)) * Decimal(str(price)) * cut, cut),
                    ('cut', 'Servicio de corte realizado', Decimal('2.5') * cut, cut),
                    ('sewing', 'Confección entregada', Decimal(str(sewing)) * sewn, sewn),
                    ('supplies', 'Insumos usados', Decimal('3.5') * cut, cut),
                ]
                if code == 'VT-003':
                    amounts.append(('other', 'Correcciones y servicio adicional', Decimal('1300'), 1))
                for index, (kind, label, amount, number) in enumerate(amounts):
                    if number:
                        record_expense(model.pk, user, {'category': kind, 'description': label, 'amount': amount.quantize(Decimal('.01')), 'paid_amount': (amount * Decimal('.7')).quantize(Decimal('.01')), 'date': today - timedelta(days=index % 6), 'supplier': workshop, 'reference': f'DEMO-{code}-{index + 1}', 'notes': 'Costo ficticio; no representa una compra real.'}, uuid.uuid4())
        Audit.objects.create(user=user, action='demo.created', description='Espacio de demostración preparado con datos ficticios')
        self.stdout.write('Demostración lista: 2 colecciones y 5 modelos. Ningún dato real fue modificado.')
