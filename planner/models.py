from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

POSITIVE = MinValueValidator(Decimal('0'))
PERCENT = [POSITIVE, MaxValueValidator(Decimal('100'))]

def money_field(label, default=0, **kwargs):
    return models.DecimalField(label, max_digits=12, decimal_places=2, default=default, validators=[POSITIVE], **kwargs)

class Project(models.Model):
    name = models.CharField('Nombre de la colección a planificar', max_length=100)
    market = models.CharField('Mercado principal', max_length=160, default='Gamarra, Lima, Perú')
    resale_cities = models.CharField('Ciudades donde se venderá o revenderá', max_length=240, blank=True)
    audience = models.CharField('Público final', max_length=160, blank=True)
    style = models.CharField('Estilo y ocasión de uso', max_length=160, blank=True)
    channel = models.CharField('Canal de venta', max_length=12, choices=[('retail','Minorista'),('wholesale','Mayorista'),('mixed','Ambos')], default='retail')
    currency = models.CharField('Moneda de este plan', max_length=3, choices=[('PEN','PEN · Soles'),('USD','USD · Dólares'),('EUR','EUR · Euros')], default='PEN')
    launch_date = models.DateField('Fecha de lanzamiento')
    sell_by = models.DateField('Fecha límite para vender')
    budget = money_field('Presupuesto total disponible')
    reserve = money_field('Reserva de efectivo (no se gasta en el plan)')
    fixed_costs = money_field('Gastos fijos de toda esta colección')
    fixed_notes = models.TextField('¿Qué incluyen los gastos fijos?', blank=True)
    tax_notes = models.CharField('Base de precios, costos e impuestos', max_length=280, default='Precios y costos en la misma base monetaria. No se calculan impuestos automáticamente.')
    assumed_sold_pct = models.DecimalField('Porcentaje vendido para tu escenario (%)', max_digits=5, decimal_places=2, default=50, validators=PERCENT)
    assumptions = models.TextField('Supuestos y decisiones que falta confirmar', blank=True)
    research_days = models.PositiveIntegerField('Ventana de investigación (días)', default=60, validators=[MinValueValidator(30),MaxValueValidator(90)])
    version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at','-pk']
    def __str__(self):
        return self.name
    @property
    def symbol(self):
        return {'PEN':'S/','USD':'US$','EUR':'€'}[self.currency]

class Product(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='products')
    name = models.CharField('Nombre del producto', max_length=100)
    description = models.TextField('Idea / descripción de la prenda', blank=True)
    reference_url = models.URLField('Enlace a una imagen o referencia visual (opcional)', max_length=600, blank=True)
    category = models.CharField('Tipo de prenda', max_length=60, blank=True)
    material = models.CharField('Material / tela', max_length=120, blank=True)
    measurements = models.TextField('Tabla de medidas / notas de tallas', blank=True)
    material_available = models.BooleanField('Material disponible y confirmado', default=False)
    cost_mode = models.CharField('Cómo registrar el costo variable', max_length=12, choices=[('complete','Costo unitario completo'),('components','Calcular con desglose')], default='complete')
    unit_cost = models.DecimalField('Costo variable de UNA prenda (sin gastos fijos)', max_digits=12, decimal_places=4, null=True, blank=True, validators=[POSITIVE])
    cost_confirmed = models.BooleanField('Costo confirmado con cotización o proveedor', default=False)
    minimum_model = models.PositiveIntegerField('Mínimo por modelo (si se produce)', default=1, validators=[MinValueValidator(1)])
    minimum_color = models.PositiveIntegerField('Mínimo por color (si se produce)', default=1, validators=[MinValueValidator(1)])
    multiple = models.PositiveIntegerField('Múltiplo de producción por variante', default=1, validators=[MinValueValidator(1)])
    capacity = models.PositiveIntegerField('Capacidad máxima para este modelo', null=True, blank=True)
    lead_days = models.PositiveIntegerField('Plazo de producción (días calendario)', default=0)
    retail_price = money_field('Precio minorista por prenda', default=None, null=True, blank=True)
    wholesale_price = money_field('Precio mayorista por prenda', default=None, null=True, blank=True)
    wholesale_share = models.DecimalField('Participación mayorista estimada (%)', max_digits=5, decimal_places=2, default=0, validators=PERCENT)
    discount = models.DecimalField('Descuento sobre precios (%)', max_digits=5, decimal_places=2, default=0, validators=PERCENT)
    commission = models.DecimalField('Comisión sobre venta después del descuento (%)', max_digits=5, decimal_places=2, default=0, validators=PERCENT)
    sale_cost = money_field('Otros costos de venta por prenda vendida')
    class Meta:
        ordering = ['pk']
    def __str__(self):
        return self.name

class Component(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='components')
    name = models.CharField('Material o servicio', max_length=120)
    quantity = models.DecimalField('Consumo por prenda', max_digits=10, decimal_places=4, validators=[MinValueValidator(Decimal('.0001'))])
    unit = models.CharField('Unidad de compra / precio', max_length=24, default='metro')
    unit_price = models.DecimalField('Precio por esa unidad', max_digits=10, decimal_places=4, validators=[POSITIVE])
    waste = models.DecimalField('Merma adicional (%)', max_digits=5, decimal_places=2, default=0, validators=PERCENT)
    class Meta:
        ordering = ['pk']

class Variant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='variants')
    color = models.CharField('Color', max_length=60)
    size = models.CharField('Talla', max_length=40)
    stock = models.PositiveIntegerField('Inventario existente', default=0)
    target = models.PositiveIntegerField('Demanda objetivo (opcional)', null=True, blank=True)
    quantity = models.PositiveIntegerField('Producción nueva', default=0)
    locked = models.BooleanField('Bloquear esta cantidad', default=False)
    available = models.BooleanField('Color / variante disponible', default=True)
    class Meta:
        ordering = ['product_id','pk']
        constraints = [models.UniqueConstraint(fields=['product','color','size'], name='unique_planner_variant')]
    def __str__(self):
        return f'{self.product.name} · {self.color} · {self.size}'

class Evidence(models.Model):
    TYPES = [('sales','Ventas propias'),('reservations','Reservas propias pendientes'),('inquiries','Consultas / encuesta'),('stockout','Sin stock / disponibilidad'),('external','Observación externa'),('assumption','Supuesto manual')]
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='evidence')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, related_name='evidence')
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, null=True, blank=True, related_name='evidence')
    kind = models.CharField('Qué tipo de evidencia es', max_length=16, choices=TYPES)
    title = models.CharField('Título / referencia del registro', max_length=180)
    units = models.PositiveIntegerField('Unidades vendidas, reservadas o consultadas', default=0)
    period_start = models.DateField('Inicio del periodo', null=True, blank=True)
    period_end = models.DateField('Fin del periodo', null=True, blank=True)
    days_in_stock = models.PositiveIntegerField('Días con stock durante ese periodo', null=True, blank=True)
    price = money_field('Precio observado / registrado', default=None, null=True, blank=True)
    url = models.URLField('Enlace a la fuente', max_length=800, blank=True)
    published_date = models.DateField('Fecha de publicación (vacía si desconocida)', null=True, blank=True)
    consulted_date = models.DateField('Fecha de consulta / registro', default=timezone.localdate)
    market = models.CharField('Mercado / región de la fuente', max_length=160, blank=True)
    source_type = models.CharField('Origen', max_length=16, choices=[('own','Mi negocio'),('local','Local'),('national','Nacional'),('international','Internacional'),('unknown','Por verificar')], default='own')
    campaign = models.CharField('Campaña / grupo de republicaciones', max_length=120, blank=True)
    signal = models.TextField('Qué observaste / qué afirma la fuente')
    limitations = models.TextField('Límites, contradicciones o datos faltantes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-consulted_date','-pk']

class ResearchRun(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='research_runs')
    fingerprint = models.CharField(max_length=64)
    query = models.TextField()
    report = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at','-pk']

class PlanVersion(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='versions')
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=12, choices=[('simulation','Simulación'),('approved','Plan aprobado')], default='simulation')
    snapshot = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at','-pk']
