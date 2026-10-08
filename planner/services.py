import json
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Project, Product, Variant, PlanVersion

ZERO=Decimal('0')
CENT=Decimal('.01')
MAX_AMOUNT=Decimal('9999999999.99')

def money(value):return Decimal(value).quantize(CENT,rounding=ROUND_HALF_UP)
def ceil_multiple(value,multiple):return int((Decimal(value)/multiple).to_integral_value(rounding=ROUND_CEILING))*multiple

def load_project(pk):
    return Project.objects.prefetch_related('products__components','products__variants','evidence').get(pk=pk)

def all_variants(project):
    return [variant for product in project.products.all() for variant in product.variants.all()]

def cost(product):
    if product.cost_mode=='complete':return product.unit_cost
    parts=list(product.components.all())
    if not parts:return None
    return sum((p.quantity*p.unit_price*(1+p.waste/100) for p in parts),ZERO).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)

def demand(project,variant):
    if variant.target is not None:
        return variant.target,'Objetivo ingresado por ti; resta el stock existente.','Baja · supuesto manual'
    evidence=[e for e in project.evidence.all() if e.variant_id==variant.pk and e.source_type=='own']
    reservations=[e for e in evidence if e.kind=='reservations']
    if reservations:
        latest=max(reservations,key=lambda e:(e.consulted_date,e.pk))
        return latest.units,f'Reservas pendientes del registro «{latest.title}». No son ventas realizadas.','Media · reservas propias'
    sales=[e for e in evidence if e.kind=='sales' and e.days_in_stock and e.period_start and e.period_end]
    if sales:
        latest=max(sales,key=lambda e:(e.period_end,e.pk))
        horizon=max(1,(project.sell_by-project.launch_date).days+1)
        target=int((Decimal(latest.units)*horizon/latest.days_in_stock).to_integral_value(rounding=ROUND_CEILING))
        target=min(target,1000000)
        return target,f'Ventas: {latest.units} / {latest.days_in_stock} días con stock × {horizon} días del plan. Solo el periodo más reciente; no suma periodos solapados.','Media · ventas propias'
    return None,'Sin historial utilizable: prueba mínima editable. Consultas y publicaciones no determinan tallas ni cantidades.','Baja · sin evidencia de venta'

def evaluate(project,variants=None,quantities=None):
    variants=list(variants if variants is not None else all_variants(project))
    quantities=quantities or {}
    products={p.pk:p for p in project.products.all()}
    costs={pk:cost(p) for pk,p in products.items()}
    rows=[];errors=[];warnings=[];product_units=defaultdict(int);color_units=defaultdict(int)
    for variant in variants:
        product=products[variant.product_id]
        quantity=int(quantities.get(variant.pk,variant.quantity))
        unit_cost=costs[product.pk]
        target,reason,confidence=demand(project,variant)
        total=money(unit_cost*quantity) if unit_cost is not None else None if quantity else ZERO
        product_units[product.pk]+=quantity;color_units[(product.pk,variant.color)]+=quantity
        if quantity<0 or quantity>1000000:errors.append(f'{product.name} · {variant.color}/{variant.size}: usa de 0 a 1 000 000 prendas.')
        if quantity:
            if unit_cost is None:errors.append(f'{product.name}: falta costo variable; no se puede validar el presupuesto.')
            if not product.material_available or not variant.available:errors.append(f'{product.name} · {variant.color}: material o variante sin disponibilidad confirmada.')
            if quantity%product.multiple:errors.append(f'{product.name} · {variant.color}/{variant.size}: la cantidad debe ser múltiplo de {product.multiple}.')
            if timezone.localdate()+timedelta(days=product.lead_days)>project.launch_date:errors.append(f'{product.name}: el plazo de {product.lead_days} días no llega al lanzamiento.')
            if not product.cost_confirmed:warnings.append(f'{product.name}: costo estimado, pendiente de confirmar antes de aprobar.')
            if target is not None and variant.stock+quantity>target:warnings.append(f'{product.name} · {variant.color}/{variant.size}: stock + producción supera el objetivo registrado; revisa esta exposición.')
        rows.append({'variant_id':variant.pk,'product_id':product.pk,'name':product.name,'color':variant.color,'size':variant.size,'stock':variant.stock,'target':target,'quantity':quantity,'locked':variant.locked,'unit_cost':unit_cost,'total':total,'reason':reason,'confidence':confidence})
    for pk,units in product_units.items():
        product=products[pk]
        if units and units<product.minimum_model:errors.append(f'{product.name}: mínimo por modelo {product.minimum_model}; el plan tiene {units}.')
        if product.capacity is not None and units>product.capacity:errors.append(f'{product.name}: capacidad {product.capacity}; el plan pide {units}.')
    for (pk,color),units in color_units.items():
        if units and units<products[pk].minimum_color:errors.append(f'{products[pk].name} · {color}: mínimo por color {products[pk].minimum_color}; el plan tiene {units}.')
    costs_complete=not any(row['quantity'] and row['unit_cost'] is None for row in rows)
    variable_total=sum((row['total'] or ZERO for row in rows),ZERO)
    committed=variable_total+project.fixed_costs
    required=committed+project.reserve
    if required>project.budget:errors.append(f'Presupuesto insuficiente: faltan {money(required-project.budget)} {project.currency} para producción + gastos fijos + reserva.')
    if required>MAX_AMOUNT:errors.append('El importe calculado supera el límite monetario de esta versión.')
    units=sum(product_units.values())
    if not units:warnings.append('No hay producción nueva. Puede no ser necesaria por el stock o no haber un lote factible; revisa objetivos y restricciones.')
    if not any(e.kind in ('sales','reservations') for e in project.evidence.all()):warnings.append('Sin ventas ni reservas propias registradas: las cantidades son pruebas o supuestos de confianza baja.')
    missing_prices=[p.name for p in products.values() if product_units[p.pk] and effective_price(project,p) is None]
    if missing_prices:warnings.append('Faltan precios para calcular escenarios de venta: '+', '.join(missing_prices)+'.')
    return {'rows':rows,'units':units,'existing_stock':sum(v.stock for v in variants),'variable':money(variable_total),'fixed':project.fixed_costs,'reserve':project.reserve,'required':money(required),'invested':money(committed),'remaining':money(project.budget-required),'costs_complete':costs_complete,'full_unit_cost':money(committed/units) if units and costs_complete else None,'errors':list(dict.fromkeys(errors)),'warnings':list(dict.fromkeys(warnings)),'feasible':not errors,'ready':bool(units) and not errors and all(products[pk].cost_confirmed for pk,count in product_units.items() if count)}

def effective_price(project,product):
    share=Decimal('0') if project.channel=='retail' else Decimal('100') if project.channel=='wholesale' else product.wholesale_share
    if (share<100 and product.retail_price is None) or (share>0 and product.wholesale_price is None):return None
    price=(product.retail_price or ZERO)*(1-share/100)+(product.wholesale_price or ZERO)*share/100
    return price*(1-product.discount/100)

def sales_scenario(project,result,pct):
    pct=Decimal(pct)
    if not 0<=pct<=100:raise ValidationError('El porcentaje vendido debe estar entre 0 y 100.')
    products={p.pk:p for p in project.products.all()}
    revenue=fees=sold_cost=stock_value=ZERO;sold=0
    margins=[]
    for row in result['rows']:
        if not row['quantity']:continue
        product=products[row['product_id']];price=effective_price(project,product)
        if price is None or row['unit_cost'] is None:return {'pct':pct,'complete':False}
        count=int((Decimal(row['quantity'])*pct/100).to_integral_value(rounding=ROUND_FLOOR))
        gross=money(count*price);charge=money(gross*product.commission/100+count*product.sale_cost)
        row_sold_cost=money(count*row['unit_cost'])
        revenue+=gross;fees+=charge;sold_cost+=row_sold_cost;stock_value+=row['total']-row_sold_cost;sold+=count
        margin=(price-row['unit_cost'])/price*100 if price else None
        markup=(price-row['unit_cost'])/row['unit_cost']*100 if row['unit_cost'] else None
        if not any(x['product_id']==product.pk for x in margins):margins.append({'product_id':product.pk,'name':product.name,'margin':money(margin) if margin is not None else None,'markup':money(markup) if markup is not None else None})
    recovered=revenue-fees
    return {'pct':pct,'complete':True,'sold':sold,'remaining_units':result['units']-sold,'revenue':money(revenue),'selling_costs':money(fees),'recovered':money(recovered),'invested':result['invested'],'cash_difference':money(recovered-result['invested']),'gross_result':money(recovered-sold_cost-project.fixed_costs),'remaining_stock_value':money(stock_value),'margins':margins}

def propose(project,factor):
    variants=all_variants(project)
    products={p.pk:p for p in project.products.all()}
    costs={pk:cost(p) for pk,p in products.items()}
    quantities={v.pk:v.quantity if v.locked else 0 for v in variants}
    goals={};notes=[]
    for variant in variants:
        goal,_,_=demand(project,variant)
        if goal is None:goals[variant.pk]=max(0,products[variant.product_id].multiple-variant.stock)
        else:goals[variant.pk]=min(1000000,max(0,int((Decimal(goal)*factor).to_integral_value(rounding=ROUND_CEILING))-variant.stock))
    def spent(candidate):
        return sum((money(costs[v.product_id]*candidate[v.pk]) for v in variants if costs[v.product_id] is not None),ZERO)+project.fixed_costs+project.reserve
    def fits(candidate,product):
        units=sum(candidate[v.pk] for v in variants if v.product_id==product.pk)
        return spent(candidate)<=project.budget and (product.capacity is None or units<=product.capacity) and all(0<=count<=1000000 for count in candidate.values())
    # Highest-priority own evidence first; stable ids break ties, never popularity online.
    def priority(product):
        evidence=[e.kind for e in project.evidence.all() if e.product_id==product.pk]
        return (0 if 'reservations' in evidence else 1 if 'sales' in evidence else 2,product.pk)
    for product in sorted(products.values(),key=priority):
        candidates=[v for v in variants if v.product_id==product.pk]
        if costs[product.pk] is None or not product.material_available or timezone.localdate()+timedelta(days=product.lead_days)>project.launch_date:
            notes.append(f'{product.name}: omitido en cantidades nuevas por costo, disponibilidad o plazo pendiente. Las cantidades bloqueadas se conservan para mostrar sus conflictos.')
            continue
        groups=defaultdict(list)
        for v in candidates:
            if v.available:groups[v.color].append(v)
        groups=sorted(groups.items(),key=lambda group:(-sum(goals[v.pk] for v in group[1]),group[0]))
        for color,group in groups:
            open_rows=[v for v in group if not v.locked and goals[v.pk]>0]
            current=sum(quantities[v.pk] for v in group)
            if not open_rows:continue
            model_current=sum(quantities[v.pk] for v in candidates)
            seed=max(0,product.minimum_color-current,product.minimum_model-model_current)
            seed=ceil_multiple(seed,product.multiple)
            if seed:
                # Weighted split in integer packs; avoid a generic size distribution.
                packs=seed//product.multiple
                total_weight=sum(max(1,goals[v.pk]) for v in open_rows)
                shares={v.pk:packs*max(1,goals[v.pk])//total_weight for v in open_rows}
                remainder=packs-sum(shares.values())
                ordered=sorted(open_rows,key=lambda v:(-(packs*max(1,goals[v.pk])%total_weight),v.pk))
                for v in ordered[:remainder]:shares[v.pk]+=1
                candidate=dict(quantities)
                for v in open_rows:candidate[v.pk]+=shares[v.pk]*product.multiple
                if not fits(candidate,product):
                    notes.append(f'{product.name} · {color}: el lote mínimo no cabe en presupuesto o capacidad. No se fuerza una compra mayor.')
                    continue
                quantities=candidate
        # Once affordable color minimums are reserved, share remaining packs
        # proportionally to the explicit unmet goals rather than filling one size first.
        eligible=[v for v in candidates if v.available and not v.locked and goals[v.pk]>0 and sum(quantities[x.pk] for x in candidates if x.color==v.color)>0]
        needs={v.pk:max(0,ceil_multiple(goals[v.pk],product.multiple)-quantities[v.pk])//product.multiple for v in eligible}
        total_need=sum(needs.values())
        def distribute(packs):
            candidate=dict(quantities)
            if not total_need:return candidate
            shares={v.pk:packs*needs[v.pk]//total_need for v in eligible}
            remainder=packs-sum(shares.values())
            ordered=sorted(eligible,key=lambda v:(-(packs*needs[v.pk]%total_need),v.pk))
            for v in ordered[:remainder]:shares[v.pk]+=1
            for v in eligible:candidate[v.pk]+=shares[v.pk]*product.multiple
            return candidate
        lo,hi=0,total_need
        while lo<hi:
            mid=(lo+hi+1)//2
            if fits(distribute(mid),product):lo=mid
            else:hi=mid-1
        quantities=distribute(lo)
    result=evaluate(project,variants,quantities)
    if not result['units'] and any(goals.values()):
        result['errors'].append('No existe un lote nuevo factible con estos objetivos, presupuesto, mínimos, disponibilidad, plazos o bloqueos. Reduce restricciones, confirma datos o revisa la fecha; no se aumenta el gasto para forzar mínimos.')
        result['feasible']=False
    result['proposal_notes']=list(dict.fromkeys(notes))
    result['assumption']=f'Objetivos con factor {factor}: 0.60 conservador, 1.00 equilibrado, 1.30 mayor exposición. Luego se resta el stock. Sin datos, se usa un lote mínimo de prueba; las etiquetas no son probabilidades de venta. Prioridad: reservas, ventas, orden de alta. No es un optimizador global.'
    return result

def freeze(project,result):
    fields=['name','market','resale_cities','audience','style','channel','currency','launch_date','sell_by','budget','reserve','fixed_costs','fixed_notes','tax_notes','assumptions','assumed_sold_pct','research_days']
    payload={'project':{name:getattr(project,name) for name in fields},'result':result,'scenarios':[sales_scenario(project,result,pct) for pct in sorted(set([Decimal('0'),project.assumed_sold_pct,Decimal('100')]))], 'evidence':list(project.evidence.values()),'products':list(project.products.values()), 'components':[]}
    for product in project.products.all():payload['components'].extend(list(product.components.values()))
    run=project.research_runs.first()
    payload['research']={'created_at':run.created_at,'query':run.query,'report':run.report} if run else None
    return json.loads(json.dumps(payload,cls=DjangoJSONEncoder))

@transaction.atomic
def save_version(pk,user,name,status='simulation'):
    Project.objects.filter(pk=pk).update(version=F('version')+1)
    project=load_project(pk)
    result=evaluate(project)
    if status=='approved' and not result['ready']:
        raise ValidationError(result['errors'] or ['Confirma costos, disponibilidad y un lote con producción nueva antes de aprobar.'])
    return PlanVersion.objects.create(project=project,name=name,status=status,snapshot=freeze(project,result),created_by=user)
