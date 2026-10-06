import uuid
from decimal import Decimal
from django import forms
from django.utils import timezone
from .models import Collection, Garment, BudgetLine, Expense, ProductionEvent

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].widget.attrs['min'] = '0.0001'
        self.fields['quantity'].help_text = 'Si se aplica a cada prenda, indica el consumo por prenda. Si es al lote, indica la cantidad total.'
        self.fields['unit_price'].help_text = 'Ejemplo: tela a S/ 10 por metro, con consumo 1.2 m por prenda.'

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
