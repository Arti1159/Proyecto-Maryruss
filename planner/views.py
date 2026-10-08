import csv
import io
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from studio.views import staff_required, errors_to_messages
from studio.services import audit
from .models import Project, Product, Component, Variant, Evidence, PlanVersion
from .forms import ProjectForm, ProductForm, ComponentForm, VariantForm, EvidenceForm, QuantityFormSet
from .services import load_project, all_variants, cost, evaluate, propose, freeze, save_version, sales_scenario
from .research import configured, run_research, evidence_report

@login_required
def index(request):
    projects=list(Project.objects.prefetch_related('products__variants','products__components','evidence'))
    for project in projects:project.summary=evaluate(project)
    return render(request,'planner/index.html',{'nav':'planner','projects':projects})

@staff_required
def project_form(request,pk=None):
    instance=get_object_or_404(Project,pk=pk) if pk else None
    form=ProjectForm(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            saved=form.save()
            audit(request.user,'planner.project',f'Planificador: {saved.name}',details={'project_id':saved.pk})
        return redirect('planner:detail',pk=saved.pk)
    return render(request,'studio/form.html',{'nav':'planner','form':form,'title':'Editar colección a planificar' if pk else 'Nueva colección a planificar','subtitle':'Decide qué producir antes de abrir un lote de producción. Todos los importes de este plan usan una sola moneda.','back':reverse('planner:detail',args=[pk]) if pk else reverse('planner:index')})

@login_required
def detail(request,pk):
    project=get_object_or_404(Project,pk=pk)
    formset=QuantityFormSet(queryset=Variant.objects.filter(product__project=project).select_related('product'),prefix='variants')
    project=load_project(pk);result=evaluate(project)
    rows={row['variant_id']:row for row in result['rows']}
    entries=[{'form':form,'row':rows[form.instance.pk]} for form in formset]
    products=list(project.products.all())
    for product in products:product.calculated_cost=cost(product)
    return render(request,'planner/detail.html',{'nav':'planner','project':project,'result':result,'formset':formset,'entries':entries,'products':products,'versions':project.versions.select_related('created_by')[:30],'research_connected':configured(),'latest_research':project.research_runs.first(),'report':evidence_report(project),'scenarios':[sales_scenario(project,result,pct) for pct in sorted(set([Decimal('0'),project.assumed_sold_pct,Decimal('100')]))]})

@staff_required
@require_POST
def quantities(request,pk,preview=False):
    with transaction.atomic():
        if not preview:Project.objects.filter(pk=pk).update(version=F('version')+1)
        project=get_object_or_404(Project,pk=pk)
        query=Variant.objects.filter(product__project=project).select_related('product')
        formset=QuantityFormSet(request.POST,queryset=query,prefix='variants')
        if not formset.is_valid():
            if preview:return JsonResponse({'valid':False,'error':'Revisa cantidades, stock y objetivos: deben ser enteros no negativos. Si cambió la lista de variantes, recarga la página.'},status=400)
            messages.error(request,'No se guardó el plan. Revisa cantidades, stock y objetivos; si cambió la lista, recarga la página.')
            return redirect(reverse('planner:detail',args=[pk])+'#variantes')
        variants=[form.instance for form in formset]
        result=evaluate(load_project(pk),variants=variants)
        if preview:return JsonResponse({'valid':True,**{key:result[key] for key in ['units','variable','fixed','reserve','required','remaining','full_unit_cost','errors','warnings','feasible','ready','costs_complete','rows']}})
        formset.save()
        audit(request.user,'planner.draft',f'Borrador actualizado: {project.name}',details={'project_id':pk,'units':result['units'],'feasible':result['feasible']})
    messages.success(request,'Borrador guardado. '+('Cabe en el presupuesto; revisa las restricciones y supuestos.' if result['feasible'] else 'Tiene conflictos señalados: sigue siendo una simulación.'))
    return redirect(reverse('planner:detail',args=[pk])+'#variantes')

@staff_required
def product_form(request,pk,product_id=None):
    project=get_object_or_404(Project,pk=pk)
    instance=get_object_or_404(Product,pk=product_id,project=project) if product_id else Product(project=project)
    form=ProductForm(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            Project.objects.filter(pk=pk).update(version=F('version')+1)
            product=form.save()
            if not product_id:
                Variant.objects.bulk_create([Variant(product=product,color=color,size=size) for color in form.cleaned_data['colors_list'] for size in form.cleaned_data['sizes_list']])
            audit(request.user,'planner.product',f'Producto de plan: {product.name}',details={'project_id':pk,'product_id':product.pk})
        return redirect(reverse('planner:detail',args=[pk])+'#productos')
    return render(request,'studio/form.html',{'nav':'planner','form':form,'title':'Editar producto del plan' if product_id else 'Añadir producto al plan','subtitle':f'{project.name} · importes en {project.currency}. Confirma costo, material y plazo antes de aprobar.','back':reverse('planner:detail',args=[pk])})

@staff_required
def child_form(request,pk,product_id,kind,child_id=None):
    project=get_object_or_404(Project,pk=pk);product=get_object_or_404(Product,pk=product_id,project=project)
    model,form_class,title=(Component,ComponentForm,'Costo variable del desglose') if kind=='component' else (Variant,VariantForm,'Variante de color y talla')
    instance=get_object_or_404(model,pk=child_id,product=product) if child_id else model(product=product)
    form=form_class(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            Project.objects.filter(pk=pk).update(version=F('version')+1)
            saved=form.save()
            audit(request.user,'planner.product_detail',f'{title}: {product.name}',details={'project_id':pk,'record_id':saved.pk,'kind':kind})
        return redirect(reverse('planner:detail',args=[pk])+'#productos')
    return render(request,'studio/form.html',{'nav':'planner','form':form,'title':title,'subtitle':f'{product.name} · {project.currency}. El desglose solo se utiliza si el producto elige «Calcular con desglose».','back':reverse('planner:detail',args=[pk])})

@staff_required
def evidence_form(request,pk,evidence_id=None):
    project=get_object_or_404(Project,pk=pk)
    instance=get_object_or_404(Evidence,pk=evidence_id,project=project) if evidence_id else Evidence(project=project)
    form=EvidenceForm(request.POST or None,instance=instance,project=project)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            saved=form.save()
            audit(request.user,'planner.evidence',f'Evidencia de {project.name}',details={'project_id':pk,'evidence_id':saved.pk,'kind':saved.kind})
        return redirect(reverse('planner:detail',args=[pk])+'#evidencia')
    return render(request,'studio/form.html',{'nav':'planner','form':form,'title':'Editar evidencia' if evidence_id else 'Añadir evidencia o supuesto','subtitle':f'{project.name} · Las ventas, reservas, consultas y señales externas se registran por separado.','back':reverse('planner:detail',args=[pk])})

@staff_required
@require_POST
def generate(request,pk):
    with transaction.atomic():
        Project.objects.filter(pk=pk).update(version=F('version')+1)
        project=load_project(pk)
        for name,factor in [('Conservador',Decimal('.60')),('Equilibrado',Decimal('1')),('Mayor exposición',Decimal('1.30'))]:
            result=propose(project,factor)
            PlanVersion.objects.create(project=project,name=name,status='simulation',snapshot=freeze(project,result),created_by=request.user)
        audit(request.user,'planner.proposed',f'Tres propuestas: {project.name}',details={'project_id':pk})
    messages.success(request,'Tres simulaciones guardadas para comparar. No se modificó el borrador. Abre una propuesta y revisa sus supuestos y conflictos antes de cargarla.')
    return redirect(reverse('planner:detail',args=[pk])+'#versiones')

@staff_required
@require_POST
def version_save(request,pk):
    status='approved' if request.POST.get('approve')=='1' else 'simulation'
    if status=='approved' and request.POST.get('reviewed')!='on':
        messages.error(request,'Confirma que revisaste cantidades, costos, restricciones y supuestos antes de aprobar.')
        return redirect('planner:detail',pk=pk)
    try:
        version=save_version(pk,request.user,'Plan revisado' if status=='approved' else 'Borrador guardado',status)
        audit(request.user,'planner.version',f'Versión de plan: {version.project.name}',details={'project_id':pk,'version_id':version.pk,'status':status})
        return redirect('planner:version',pk=pk,version_id=version.pk)
    except ValidationError as error:errors_to_messages(request,error)
    return redirect('planner:detail',pk=pk)

@login_required
def version_detail(request,pk,version_id):
    version=get_object_or_404(PlanVersion,pk=version_id,project_id=pk)
    current=evaluate(load_project(pk))
    current_rows={row['variant_id']:row for row in current['rows']}
    data=dict(version.snapshot)
    data['result']=dict(data['result'])
    data['result']['rows']=[dict(row,current_quantity=current_rows.get(row['variant_id'],{}).get('quantity'),quantity_delta=row['quantity']-current_rows.get(row['variant_id'],{}).get('quantity',0)) for row in data['result']['rows']]
    delta=Decimal(data['result']['variable'])-current['variable'] if data['project']['currency']==version.project.currency else None
    return render(request,'planner/version.html',{'nav':'planner','version':version,'data':data,'project':version.project,'current':current,'delta':delta})

@staff_required
@require_POST
def apply_version(request,pk,version_id):
    version=get_object_or_404(PlanVersion,pk=version_id,project_id=pk)
    with transaction.atomic():
        Project.objects.filter(pk=pk).update(version=F('version')+1)
        variants={v.pk:v for v in Variant.objects.filter(product__project_id=pk)}
        if {row['variant_id'] for row in version.snapshot['result']['rows']}!=set(variants):
            messages.error(request,'La lista de variantes cambió. Genera una propuesta nueva antes de cargarla.')
            return redirect('planner:version',pk=pk,version_id=version_id)
        for row in version.snapshot['result']['rows']:
            if row['variant_id'] not in variants:
                messages.error(request,'La estructura de variantes cambió. No se puede cargar esta versión; crea una propuesta nueva.')
                return redirect('planner:version',pk=pk,version_id=version_id)
            if variants[row['variant_id']].locked and variants[row['variant_id']].quantity!=row['quantity']:
                messages.error(request,'Una cantidad bloqueada entra en conflicto con esta versión. Desbloquéala explícitamente si quieres reemplazarla.')
                return redirect('planner:version',pk=pk,version_id=version_id)
        for row in version.snapshot['result']['rows']:Variant.objects.filter(pk=row['variant_id'],product__project_id=pk).update(quantity=row['quantity'])
        audit(request.user,'planner.loaded',f'Propuesta cargada en borrador: {version.name}',details={'project_id':pk,'version_id':version_id})
    messages.success(request,'Cantidades cargadas al borrador. Se recalculan con los costos actuales; la versión guardada conserva los importes y evidencia anteriores.')
    return redirect(reverse('planner:detail',args=[pk])+'#variantes')

@staff_required
@require_POST
def research(request,pk):
    project=load_project(pk)
    try:
        run,cached=run_research(project,force=request.POST.get('refresh')=='1')
        audit(request.user,'planner.research',f'Investigación de {project.name}',details={'project_id':pk,'run_id':run.pk,'cached':cached})
        messages.success(request,'Se muestra la consulta conservada de las últimas 6 horas.' if cached else 'Fuentes reales consultadas. Revisa fechas, mercado y limitaciones antes de usarlas como evidencia.')
    except ValidationError as error:errors_to_messages(request,error)
    return redirect(reverse('planner:detail',args=[pk])+'#evidencia')

@login_required
def export(request,pk,version_id,entity):
    version=get_object_or_404(PlanVersion,pk=version_id,project_id=pk);data=version.snapshot
    output=io.StringIO();writer=csv.writer(output)
    def row(values):writer.writerow([("'"+str(v)) if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else '' if v is None else v for v in values])
    if entity=='plan':
        row(['Versión','Estado','Moneda','Modelo','Color','Talla','Stock existente','Demanda objetivo','Producción nueva','Costo variable unitario','Costo variable total','Confianza','Explicación'])
        for r in data['result']['rows']:row([version.name,version.get_status_display(),data['project']['currency'],r['name'],r['color'],r['size'],r['stock'],r['target'],r['quantity'],Decimal(r['unit_cost']) if r['unit_cost'] is not None else None,Decimal(r['total']) if r['total'] is not None else None,r['confidence'],r['reason']])
        row(['TOTALES' if data['result']['costs_complete'] else 'TOTALES PARCIALES: COSTOS FALTANTES',None,data['project']['currency'],None,None,None,None,None,data['result']['units'],None,Decimal(data['result']['variable'])])
        for key in ('fixed','reserve','required','remaining'):row([key,None,data['project']['currency'],Decimal(data['result'][key])])
    elif entity=='evidencia':
        fields=['kind','title','variant_id','units','period_start','period_end','days_in_stock','price','url','published_date','consulted_date','market','source_type','campaign','signal','limitations']
        row(fields)
        for record in data['evidence']:row([record.get(field) for field in fields])
    elif entity=='supuestos':
        row(['Campo','Valor'])
        for key,value in data['project'].items():row([key,value])
        row(['Regla de propuesta',data['result'].get('assumption','Borrador manual; cantidades ingresadas por el usuario.')])
        for warning in data['result']['warnings']:row(['Advertencia',warning])
        for error in data['result']['errors']:row(['Conflicto',error])
    else:raise Http404
    response=HttpResponse('\ufeff'+output.getvalue(),content_type='text/csv; charset=utf-8')
    response['Content-Disposition']=f'attachment; filename="maryruss-plan-{version.pk}-{entity}.csv"'
    return response
