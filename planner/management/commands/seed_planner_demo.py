from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from planner.models import Project,Product,Variant,Evidence,PlanVersion
from planner.services import load_project,propose,freeze
from decimal import Decimal

class Command(BaseCommand):
    help='Crea un planificador de demostración ficticio, únicamente en modo demo.'
    @transaction.atomic
    def handle(self,*args,**options):
        if not settings.DEMO_MODE:raise CommandError('La demostración de planificación solo se crea con MARYRUSS_DEMO=1.')
        if Project.objects.exists():
            self.stdout.write('Ya hay planes en esta demo; se conservan sin cambios.')
            return
        today=timezone.localdate()
        project=Project.objects.create(name='DEMO · Colección de prueba para mi tienda',market='Gamarra, Lima, Perú',resale_cities='Lima · destinos por confirmar',audience='Ejemplo ficticio',style='Ropa casual de prueba',channel='mixed',launch_date=today+timedelta(days=30),sell_by=today+timedelta(days=75),budget=3000,reserve=400,fixed_costs=200,fixed_notes='Ejemplo: fotos y traslado fijo. No son cotizaciones reales.',assumptions='DATOS FICTICIOS. Cantidades y precios para aprender a usar la herramienta; no son datos del mercado ni pronósticos.',assumed_sold_pct=50)
        blouse=Product.objects.create(project=project,name='DEMO · Blusa casual',material='Algodón de ejemplo',material_available=True,unit_cost=25,cost_confirmed=True,minimum_model=12,minimum_color=6,multiple=2,capacity=80,lead_days=14,retail_price=55,wholesale_price=42,wholesale_share=30)
        for color in ('Negro','Marfil'):
            for size in ('S','M','L'):
                variant=Variant.objects.create(product=blouse,color=color,size=size,stock=2 if color=='Negro' else 0,target=12)
                Evidence.objects.create(project=project,product=blouse,variant=variant,kind='assumption',title=f'DEMO · Prueba {color}/{size}',signal='Objetivo ficticio de 12 prendas para probar una variante. No procede de ventas reales.',source_type='own',limitations='Supuesto ilustrativo, no recomendación de demanda.')
        user=get_user_model().objects.filter(username='demo',is_staff=True).first()
        if user:
            plan=load_project(project.pk)
            for name,factor in [('Conservador',Decimal('.60')),('Equilibrado',Decimal('1')),('Mayor exposición',Decimal('1.30'))]:
                PlanVersion.objects.create(project=project,name='DEMO · '+name,snapshot=freeze(plan,propose(plan,factor)),created_by=user)
        self.stdout.write('Planificador demo creado con supuestos y precios claramente ficticios.')
