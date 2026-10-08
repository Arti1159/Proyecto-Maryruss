import uuid
from decimal import Decimal
from django import forms
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse
from .models import Collection, Garment, BudgetLine, Expense, ProductionEvent, ExpenseCategory

def configure_categories(form):
    query = Q(active=True)
    if form.instance.pk:
        query |= Q(pk=form.instance.category_id)
    form.fields['category'].queryset = ExpenseCategory.objects.filter(query)
    form.fields['category'].empty_label = 'Elige una categoría de gasto'
    form.fields['category'].widget.attrs['data-category-options-url'] = reverse('category_options')
    if form.instance.pk:
        form.fields['category'].widget.attrs['data-existing-category'] = form.instance.category_id
    form.category_settings = True

class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description']
        widgets = {'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ej.: Bordado'}), 'description': forms.Textarea(attrs={'class': 'input', 'rows': 3, 'placeholder': 'Ej.: Bordado del logo y aplicaciones decorativas.'})}
        help_texts = {'name': 'Este nombre aparecerá en presupuestos, costos reales, filtros y reportes.', 'description': 'Opcional. Describe qué registrar aquí para evitar confusiones.'}

    def clean_name(self):
        name = ' '.join(self.cleaned_data['name'].split())
        if not name:
            raise forms.ValidationError('Escribe un nombre para la categoría.')
        names = ExpenseCategory.objects.exclude(pk=self.instance.pk).values_list('name', flat=True)
        if any(existing.casefold() == name.casefold() for existing in names):
            raise forms.ValidationError('Ya existe una categoría con ese nombre, incluso si está archivada. Puedes reactivarla desde Ajustes.')
        return name

class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'input')
            if isinstance(field, forms.DecimalField):
                field.localize = False
                field.widget.attrs['step'] = '0.01' if field.decimal_places == 2 else '0.0001'
                field.widget.attrs['min'] = '0'
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'input'})
            if isinstance(field, forms.CharField) and isinstance(field.widget, forms.Textarea):
                field.widget.attrs['rows'] = 3

class CollectionForm(StyledForm):
    class Meta:
        model = Collection
        fields = ['name', 'season', 'budget', 'due_date', 'notes']

class GarmentForm(StyledForm):
    class Meta:
        model = Garment
        fields = ['collection', 'code', 'name', 'category', 'planned_units', 'color', 'sizes', 'workshop', 'due_date', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['collection'].queryset = Collection.objects.filter(archived=False)
        self.fields['planned_units'].widget.attrs.update({'min': '1', 'max': '1000000'})
        self.fields['sizes'].help_text = 'Referencia manual, por ejemplo: S 10 · M 20 · L 10. Esta versión controla cantidades por modelo.'

    def clean_planned_units(self):
        units = self.cleaned_data['planned_units']
        if units > 1000000:
            raise forms.ValidationError('Usa como máximo 1 000 000 de unidades por modelo.')
        if self.instance.pk:
            cut = sum(e.quantity for e in self.instance.events.filter(stage='cut', voided=False))
            if units < cut:
                raise forms.ValidationError('No puede ser menor que las unidades ya cortadas.')
        return units

    def clean_collection(self):
        collection = self.cleaned_data['collection']
        if self.instance.pk:
            original = Garment.objects.get(pk=self.instance.pk)
            if collection.pk != original.collection_id and (original.approved_budget is not None or original.events.exists() or original.expenses.exists()):
                raise forms.ValidationError('Un modelo con presupuesto aprobado u operaciones no puede cambiar de colección.')
        return collection

class BudgetLineForm(StyledForm):
    class Meta:
        model = BudgetLine
        fields = ['category', 'description', 'basis', 'quantity', 'unit', 'unit_price']
        labels = {'description': '¿Qué vas a presupuestar?', 'basis': '¿Cómo se aplica este costo?', 'quantity': 'Cantidad que usa una prenda', 'unit': 'Unidad de medida', 'unit_price': 'Precio por unidad de medida (S/)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configure_categories(self)
        self.fields['basis'].choices = [('unit', 'Se repite en cada prenda'), ('batch', 'Es un costo para todo el lote')]
        self.fields['quantity'].widget.attrs['min'] = '0.0001'
        current_basis = self.data.get('basis') if self.is_bound else self.initial.get('basis', self.instance.basis)
        if current_basis == 'batch':
            self.fields['quantity'].label = 'Cantidad total para este costo'
        self.fields['description'].widget.attrs['placeholder'] = 'Ej.: Tela principal de algodón'
        self.fields['unit'].widget.attrs.update({'list': 'budget-unit-options', 'placeholder': 'Ej.: metro, prenda o servicio'})
        self.fields['unit_price'].widget.attrs['placeholder'] = 'Ej.: 10.00'
        self.fields['category'].help_text = 'Agrupa el costo para compararlo luego con los gastos reales.'
        self.fields['description'].help_text = 'Nombra el material o servicio específico que necesitas.'
        self.fields['basis'].help_text = 'Por prenda: se multiplica por las unidades del modelo. Por lote: se registra una sola vez.'
        self.fields['quantity'].help_text = 'Ej.: 1.2 metros de tela para una prenda. Para un costo por lote, usa la cantidad total.'
        self.fields['unit'].help_text = 'Es la unidad en la que compras o pagas: metro, kilo, prenda, hora o servicio.'
        self.fields['unit_price'].help_text = 'Precio de UN metro, kilo, prenda o servicio, según la unidad elegida.'
        tips = {
            'category': 'Ej.: Tela para materiales textiles, Confección para el taller. Puedes crear tus propias categorías en Ajustes.',
            'description': 'Ej.: Tela principal, botones de nácar, confección del vestido o traslado al taller. Cada concepto tiene su propia cantidad y precio.',
            'basis': 'Si una prenda necesita 1.2 m de tela, elige por prenda. Si pagarás S/ 80 por transportar todo el lote, elige por lote, cantidad 1, unidad servicio y precio 80.',
            'quantity': 'Esta cantidad mide material o servicios, no el número de prendas del modelo. Ese número ya está en la ficha del modelo. Para confección a S/ 15 por prenda: cantidad 1, unidad prenda y precio 15.',
            'unit': 'Cantidad y precio deben usar la misma unidad. Si pones metro, el precio es por metro; si pones servicio, el precio es por un servicio.',
            'unit_price': 'Con 1.2 metros por prenda a S/ 10 por metro, cada prenda cuesta S/ 12 en este concepto. En un modelo de 500 prendas, el total es S/ 6 000. Puedes incluir un costo previsto de cero.',
        }
        for name, tip in tips.items():
            self.fields[name].info_text = tip
            self.fields[name].widget.attrs['aria-describedby'] = f'id_{name}_help'

    def clean(self):
        values = super().clean()
        for name in ('description', 'unit'):
            if name in values and not values[name].strip():
                self.add_error(name, 'Escribe un valor; no puede contener solo espacios.')
        return values

class OperationForm(StyledForm):
    token = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['token'].initial = uuid.uuid4()
        self.fields['garment'].queryset = Garment.objects.filter(archived=False, collection__archived=False).select_related('collection')
        self.fields['garment'].label_from_instance = lambda obj: f'{obj.code} · {obj.name} — {obj.collection.name}'

    def clean_date(self):
        date = self.cleaned_data['date']
        if date > timezone.localdate():
            raise forms.ValidationError('Usa una fecha de hoy o anterior para una operación realizada.')
        return date

class ExpenseForm(OperationForm):
    class Meta:
        model = Expense
        fields = ['garment', 'category', 'description', 'amount', 'paid_amount', 'date', 'supplier', 'reference', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configure_categories(self)
        self.fields['category'].help_text = 'Usa la misma categoría del presupuesto para comparar lo previsto con el costo real.'

    def clean(self):
        values = super().clean()
        if values.get('paid_amount') is not None and values.get('amount') is not None and values['paid_amount'] > values['amount']:
            self.add_error('paid_amount', 'El pago no puede superar el costo registrado.')
        return values

class ProductionForm(OperationForm):
    class Meta:
        model = ProductionEvent
        fields = ['garment', 'stage', 'quantity', 'date', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].widget.attrs['min'] = '1'
        self.fields['quantity'].help_text = 'Registra solo unidades que avanzaron ahora, no el total acumulado. Antes deben haber completado la etapa anterior.'

class PaidForm(forms.Form):
    paid_amount = forms.DecimalField(label='Total pagado acumulado (S/)', max_digits=12, decimal_places=2, min_value=Decimal('0'), widget=forms.NumberInput(attrs={'class': 'input', 'step': '0.01', 'min': '0'}))

class VoidForm(forms.Form):
    reason = forms.CharField(label='Motivo de la anulación', max_length=240, widget=forms.Textarea(attrs={'class': 'input', 'rows': 3}))
