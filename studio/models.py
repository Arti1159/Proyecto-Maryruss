import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

ZERO = Decimal('0')
STAGES = [('cut', 'Corte'), ('sewing', 'Confección'), ('finishing', 'Acabados'),
          ('approved', 'Aprobadas por calidad'), ('rejected', 'Rechazadas por calidad')]

def category_code():
    return 'custom_' + uuid.uuid4().hex

class ExpenseCategory(models.Model):
    code = models.CharField(primary_key=True, max_length=48, default=category_code, editable=False)
    name = models.CharField('Nombre de la categoría', max_length=60)
    description = models.CharField('¿Qué gastos incluye?', max_length=280, blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name', 'code']
        constraints = [models.UniqueConstraint(Lower('name'), name='unique_expense_category_name')]

    def __str__(self):
        return self.name if self.active else f'{self.name} (archivada)'

class CategorizedCost(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, db_column='category', verbose_name='Categoría de gasto')

    class Meta:
        abstract = True

    def get_category_display(self):
        return self.category.name

    def clean(self):
        super().clean()
        if self.category_id and ExpenseCategory.objects.filter(pk=self.category_id, active=False).exists():
            original = type(self).objects.filter(pk=self.pk).values_list('category_id', flat=True).first() if self.pk else None
            if original != self.category_id:
                raise ValidationError({'category': 'Esta categoría está archivada. Elige una activa o reactívala en Ajustes.'})

class Collection(models.Model):
    name = models.CharField('Nombre', max_length=100)
    season = models.CharField('Temporada / campaña', max_length=100, blank=True)
    budget = models.DecimalField('Presupuesto disponible (S/)', max_digits=12, decimal_places=2, validators=[MinValueValidator(ZERO)])
    due_date = models.DateField('Fecha objetivo', blank=True, null=True)
    notes = models.TextField('Notas', blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=models.Q(budget__gte=0), name='collection_budget_positive')]

    def __str__(self):
        return self.name

class Garment(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT, related_name='garments', verbose_name='Colección')
    code = models.CharField('Código', max_length=32)
    name = models.CharField('Nombre del modelo', max_length=100)
    category = models.CharField('Tipo de prenda', max_length=16, choices=[('blouse', 'Blusa'), ('shirt', 'Polo / camisa'), ('dress', 'Vestido'), ('pants', 'Pantalón'), ('jacket', 'Casaca / chaqueta'), ('other', 'Otro')], default='blouse')
    color = models.CharField('Colores', max_length=100, blank=True)
    sizes = models.CharField('Tallas / distribución', max_length=150, blank=True)
    planned_units = models.PositiveIntegerField('Unidades previstas', validators=[MinValueValidator(1)])
    approved_units = models.PositiveIntegerField(default=0)
    approved_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    approved_snapshot = models.JSONField(default=dict, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    workshop = models.CharField('Taller / responsable', max_length=100, blank=True)
    due_date = models.DateField('Fecha de entrega', null=True, blank=True)
    notes = models.TextField('Ficha y observaciones', blank=True)
    archived = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code', 'id']
        constraints = [
            models.UniqueConstraint(fields=['collection', 'code'], name='unique_model_code_collection'),
            models.CheckConstraint(condition=models.Q(planned_units__gte=1), name='model_units_positive'),
        ]

    def __str__(self):
        return f'{self.code} · {self.name}'

class BudgetLine(CategorizedCost):
    garment = models.ForeignKey(Garment, on_delete=models.PROTECT, related_name='budget_lines')
    description = models.CharField('Concepto', max_length=120)
    basis = models.CharField('Se aplica', max_length=12, choices=[('unit', 'A cada prenda'), ('batch', 'Una vez al lote')], default='unit')
    quantity = models.DecimalField('Cantidad / consumo', max_digits=10, decimal_places=4, default=1, validators=[MinValueValidator(Decimal('0.0001'))])
    unit = models.CharField('Unidad', max_length=24, default='unidad')
    unit_price = models.DecimalField('Precio por unidad de insumo (S/)', max_digits=10, decimal_places=4, validators=[MinValueValidator(ZERO)])

    class Meta:
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0) & models.Q(unit_price__gte=0), name='valid_budget_line')]

class Expense(CategorizedCost):
    garment = models.ForeignKey(Garment, on_delete=models.PROTECT, related_name='expenses', verbose_name='Modelo')
    description = models.CharField('Concepto', max_length=160)
    amount = models.DecimalField('Costo real total (S/)', max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    paid_amount = models.DecimalField('Importe pagado (S/)', max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(ZERO)])
    date = models.DateField('Fecha', default=timezone.localdate)
    supplier = models.CharField('Proveedor / taller', max_length=100, blank=True)
    reference = models.CharField('Comprobante / referencia', max_length=80, blank=True)
    notes = models.TextField('Observaciones', blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0) & models.Q(paid_amount__gte=0) & models.Q(paid_amount__lte=models.F('amount')), name='valid_expense_amounts')]

class ProductionEvent(models.Model):
    garment = models.ForeignKey(Garment, on_delete=models.PROTECT, related_name='events', verbose_name='Modelo')
    stage = models.CharField('Etapa completada', max_length=16, choices=STAGES)
    quantity = models.PositiveIntegerField('Unidades adicionales', validators=[MinValueValidator(1)])
    date = models.DateField('Fecha', default=timezone.localdate)
    notes = models.TextField('Observaciones', blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gte=1), name='event_quantity_positive')]

class Audit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    description = models.CharField(max_length=250)
    garment = models.ForeignKey(Garment, on_delete=models.PROTECT, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
