from django import forms
from django.forms import BaseModelFormSet, modelformset_factory
from studio.forms import StyledForm as StudioForm
from django.utils import timezone
from .models import Project, Product, Component, Variant, Evidence

class StyledForm(StudioForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            if isinstance(field.widget,forms.CheckboxInput):field.widget.attrs['class']='checkbox-choice'

class ProjectForm(StyledForm):
    class Meta:
        model = Project
        fields = ['name','market','resale_cities','audience','style','channel','currency','launch_date','sell_by','budget','reserve','fixed_costs','fixed_notes','tax_notes','research_days','assumed_sold_pct','assumptions']
        help_texts = {
            'budget':'Incluye producción nueva, gastos fijos de esta colección y reserva. No se añade el valor del stock existente.',
            'reserve':'Dinero que decides conservar sin gastar. No hay un porcentaje obligatorio.',
            'fixed_costs':'Un solo total para gastos que no cambian por prenda. No los incluyas otra vez en el costo variable de los productos.',
            'fixed_notes':'Ej.: sesión de fotos, traslado fijo o alquiler para esta campaña. Anota lo incluido para evitar duplicaciones.',
            'currency':'Todos los importes del proyecto usan esta moneda. Cambiarla no convierte valores: revisa los importes.',
            'resale_cities':'El clima y calendario de venta corresponden al comprador final, no necesariamente al lugar de fabricación.',
            'tax_notes':'Aclara si precios y costos incluyen impuestos. El resultado es bruto estimado; no se hace una determinación tributaria.',
            'assumed_sold_pct':'Supuesto editable para comparar caja y resultado bruto. No es una predicción ni probabilidad de venta.',
            'research_days':'Entre 30 y 90 días. Una fecha de consulta no prueba que una publicación sea reciente.',
        }
    def clean(self):
        data = super().clean()
        if data.get('launch_date') and data.get('sell_by') and data['sell_by'] < data['launch_date']:
            self.add_error('sell_by','Debe ser igual o posterior al lanzamiento.')
        return data

class ProductForm(StyledForm):
    colors = forms.CharField(label='Colores disponibles, separados por comas', max_length=700, required=False, help_text='Solo al crear el producto. Ej.: Negro, Marfil. Sin dato se crea un color Único pendiente de confirmar.')
    sizes = forms.CharField(label='Tallas, separadas por comas', max_length=500, required=False, help_text='Solo al crear el producto. Usa tus tallas reales; no se presupone una distribución S/M/L. Sin dato se crea talla Única.')
    class Meta:
        model = Product
        fields = ['name','description','reference_url','category','material','measurements','material_available','cost_mode','unit_cost','cost_confirmed','minimum_model','minimum_color','multiple','capacity','lead_days','retail_price','wholesale_price','wholesale_share','discount','commission','sale_cost']
        help_texts = {
            'reference_url':'Enlace a tu foto o ficha de referencia. No se analiza automáticamente la imagen.',
            'unit_cost':'Todo el costo variable de una prenda, incluyendo materiales, confección e insumos. Excluye los gastos fijos de la colección.',
            'cost_mode':'Solo se utiliza el método elegido: el costo completo o la suma del desglose. Nunca se suman ambos.',
            'cost_confirmed':'Sin confirmar, el plan se guarda como simulación y no puede aprobarse.',
            'material_available':'Confirma tela y materiales antes de proponer producción. Si no hay disponibilidad, las propuestas omiten este producto.',
            'minimum_color':'Se exige para cada color que tenga producción nueva. Un color sin producción no necesita cumplir un mínimo.',
            'multiple':'Se aplica por color y talla. Ej.: 5 permite 0, 5, 10… prendas por variante.',
            'capacity':'Vacío: sin límite declarado. Cero: no hay capacidad para fabricar este producto.',
            'lead_days':'La entrega estimada es hoy + estos días calendario. Debe llegar a tiempo para el lanzamiento.',
            'wholesale_share':'0 = todo minorista, 100 = todo mayorista. En canales mixtos es un supuesto editable.',
        }
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance.pk:
            self.fields.pop('colors')
            self.fields.pop('sizes')
        for name in ['minimum_model','minimum_color','multiple','capacity','lead_days']:
            self.fields[name].widget.attrs.update({'min':'0' if name in ('capacity','lead_days') else '1','max':'1000000'})
    def clean(self):
        data=super().clean()
        for field in ('minimum_model','minimum_color','multiple','capacity','lead_days'):
            if data.get(field) is not None and data[field]>1000000:
                self.add_error(field,'Usa como máximo 1 000 000.')
        if not self.instance.pk:
            for field, fallback, limit in [('colors','Único',60),('sizes','Única',40)]:
                parts=list(dict.fromkeys(x.strip() for x in data.get(field,'').split(',') if x.strip())) or [fallback]
                if any(len(part)>limit for part in parts):self.add_error(field,f'Cada valor admite hasta {limit} caracteres.')
                data[field+'_list']=parts
            new_count=len(data.get('colors_list',[]))*len(data.get('sizes_list',[]))
            if Variant.objects.filter(product__project_id=self.instance.project_id).count()+new_count>1000:
                self.add_error('colors','El proyecto admite como máximo 1 000 variantes. Reduce los colores o tallas.')
            if new_count>60:
                self.add_error('colors','Limita el producto a 60 variantes; puedes comenzar con menos colores y tallas.')
        return data

class ComponentForm(StyledForm):
    class Meta:
        model=Component
        fields=['name','quantity','unit','unit_price','waste']
        help_texts={'quantity':'Cantidad necesaria para UNA prenda, en la misma unidad del precio.', 'waste':'Merma ADICIONAL. Si la cantidad o el costo ya incluye merma, deja cero para evitar duplicarla.', 'unit_price':'Precio por un metro, kilo, unidad o servicio. La merma aumenta la cantidad, no se suma como un segundo costo.'}

class VariantForm(StyledForm):
    class Meta:
        model=Variant
        fields=['color','size','stock','target','quantity','locked','available']
        help_texts={'stock':'Prendas disponibles antes de fabricar. Se descuentan de la demanda objetivo al proponer producción nueva.', 'target':'Cantidad total que deseas atender, incluyendo stock. Es tu supuesto, no una venta garantizada.', 'locked':'Las propuestas respetan esta cantidad, incluso si es cero. Si causa un conflicto, se explica.', 'available':'Desmárcalo si este color o variante requiere cotización o no puede fabricarse.'}
    def clean(self):
        data=super().clean()
        for name in ('stock','target','quantity'):
            if data.get(name) is not None and data[name]>1000000:self.add_error(name,'Usa como máximo 1 000 000.')
        if not self.instance.pk and self.instance.product_id and Variant.objects.filter(product__project_id=self.instance.product.project_id).count()>=1000:
            self.add_error(None,'El proyecto admite como máximo 1 000 variantes.')
        if data.get('color') and data.get('size'):
            rows=Variant.objects.filter(product_id=self.instance.product_id).exclude(pk=self.instance.pk).values_list('color','size')
            if any(color.casefold()==data['color'].casefold() and size.casefold()==data['size'].casefold() for color,size in rows):
                self.add_error('size','Esta combinación de color y talla ya existe en el producto.')
        return data

class QuantityForm(VariantForm):
    class Meta(VariantForm.Meta):
        fields=['stock','target','quantity','locked']

class ProjectVariantFormSet(BaseModelFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):return
        expected=set(self.get_queryset().values_list('pk',flat=True))
        supplied=[form.cleaned_data['id'].pk for form in self.forms if form.cleaned_data.get('id')]
        if len(supplied)!=len(set(supplied)) or set(supplied)!=expected:
            raise forms.ValidationError('Las variantes cambiaron o el formulario está incompleto. Recarga el plan antes de guardar.')

QuantityFormSet=modelformset_factory(Variant,form=QuantityForm,formset=ProjectVariantFormSet,extra=0,max_num=1000,absolute_max=1000,validate_max=True)

class EvidenceForm(StyledForm):
    class Meta:
        model=Evidence
        fields=['product','variant','kind','title','units','period_start','period_end','days_in_stock','price','url','published_date','consulted_date','market','source_type','campaign','signal','limitations']
        help_texts={'kind':'Ventas, reservas, consultas y publicaciones se mantienen separadas. Consultas y tendencias no se cuentan como ventas.', 'days_in_stock':'Permite leer ventas por día de disponibilidad. Cero o vacío: no se infiere una tasa de venta.', 'published_date':'Vacía si la fuente no tiene fecha. La fecha de consulta no reemplaza la fecha de publicación.', 'campaign':'Agrupa republicaciones de la misma campaña para no contarlas como señales independientes.', 'variant':'Para proponer tallas y cantidades con ventas propias, identifica la variante y el periodo con días de stock.'}
    def __init__(self,*args,project,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['product'].queryset=project.products.all()
        self.fields['variant'].queryset=Variant.objects.filter(product__project=project).select_related('product')
    def clean(self):
        data=super().clean()
        variant,product=data.get('variant'),data.get('product')
        if variant:
            if product and variant.product_id!=product.pk:self.add_error('variant','La variante debe pertenecer al producto seleccionado.')
            data['product']=variant.product
        start,end=data.get('period_start'),data.get('period_end')
        if start and end and end<start:self.add_error('period_end','El fin no puede ser anterior al inicio.')
        if start and end and end>=start and data.get('days_in_stock') is not None and data['days_in_stock']>(end-start).days+1:
            self.add_error('days_in_stock','No puede superar los días del periodo registrado.')
        if data.get('kind') in ('sales','reservations') and data.get('source_type')!='own':
            self.add_error('source_type','Ventas y reservas propias deben tener origen Mi negocio. Para publicaciones de tiendas, usa Observación externa.')
        today=timezone.localdate()
        for name in ('period_end','published_date','consulted_date'):
            if data.get(name) and data[name]>today:self.add_error(name,'Usa una fecha de hoy o anterior para evidencia observada.')
        return data
