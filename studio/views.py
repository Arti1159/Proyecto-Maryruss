import csv
import io
from datetime import timedelta
from decimal import Decimal
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import CollectionForm, GarmentForm, BudgetLineForm, ExpenseForm, ProductionForm, PaidForm, VoidForm
from .models import Collection, Garment, BudgetLine, Expense, ProductionEvent, Audit, CATEGORIES
from .services import enrich, summarize, snapshot, line_total, money, audit, lock_model, check_active, check_amounts, approve_budget, record_event, record_expense, void_record, set_paid

ZERO = Decimal('0.00')

def staff_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied('Esta operación requiere un responsable administrador.')
        return view(request, *args, **kwargs)
    return wrapped

def base_models():
    return Garment.objects.select_related('collection').prefetch_related('budget_lines', 'events', 'expenses')

def selected_collection(request, include_archived=False):
    collections = Collection.objects.all()
    if not include_archived:
        collections = collections.filter(archived=False)
    key = request.GET.get('collection', '')
    selected = collections.filter(pk=key).first() if key.isascii() and key.isdigit() else None
    return collections, selected

def totals(items):
    result = {key: sum((x.summary[key] for x in items), ZERO) for key in ['planned', 'baseline', 'actual', 'paid', 'unpaid']}
    result.update(units=sum(x.summary['units'] for x in items), good=sum(x.summary['good'] for x in items),
                  approved=sum((x.approved_budget or ZERO for x in items), ZERO), count=len(items),
                  approved_count=sum(x.approved_budget is not None for x in items),
                  overdue=sum(x.summary['overdue'] for x in items),
                  over_count=sum(x.summary['over_budget'] for x in items))
    result['progress'] = round(100 * result['good'] / result['units']) if result['units'] else 0
    return result

def errors_to_messages(request, error):
    for item in error.messages:
        messages.error(request, item)

@login_required
def dashboard(request):
    collections, selected = selected_collection(request)
    query = base_models().filter(collection__archived=False)
    if selected:
        query = query.filter(collection=selected)
    models = enrich(query)
    figures = totals(models)
    available = selected.budget if selected else sum((c.budget for c in collections), ZERO)
    figures['available'] = available
    figures['unallocated'] = available - figures['approved']
    figures['cost_balance'] = available - figures['actual']
    ids = [m.pk for m in models]
    expenses = list(Expense.objects.filter(garment_id__in=ids, voided=False).select_related('garment'))
    max_day = timezone.localdate()
    chart = []
    for days in range(6, -1, -1):
        day = max_day - timedelta(days=days)
        amount = sum((e.amount for e in expenses if e.date == day), ZERO)
        chart.append({'date': day, 'amount': amount})
    peak = max((x['amount'] for x in chart), default=ZERO)
    for bar in chart:
        bar['height'] = max(4, int(100 * bar['amount'] / peak)) if peak and bar['amount'] else 0
    category_totals = [{'label': label, 'amount': sum((e.amount for e in expenses if e.category == key), ZERO), 'key': key} for key, label in CATEGORIES]
    category_totals = sorted([x for x in category_totals if x['amount']], key=lambda x: x['amount'], reverse=True)
    for category in category_totals:
        category['pct'] = round(category['amount'] * 100 / figures['actual']) if figures['actual'] else 0
    collections_list = []
    for collection in collections:
        if selected and collection.pk != selected.pk:
            continue
        collection.summary = totals([m for m in models if m.collection_id == collection.pk])
        collections_list.append(collection)
    return render(request, 'studio/dashboard.html', {
        'nav': 'dashboard', 'collections': collections, 'selected': selected,
        'figures': figures, 'models': sorted(models, key=lambda x: (not x.summary['overdue'], not x.summary['over_budget'], x.code))[:6],
        'chart': chart, 'chart_total': sum((x['amount'] for x in chart), ZERO),
        'category_totals': category_totals[:5], 'collection_cards': collections_list[:3],
        'recent': Audit.objects.select_related('user', 'garment').filter(garment_id__in=ids)[:5],
    })

@login_required
def collection_list(request):
    archived = request.GET.get('archived') == '1'
    collections = list(Collection.objects.filter(archived=archived))
    models = enrich(base_models().filter(collection__in=collections))
    for collection in collections:
        collection.summary = totals([m for m in models if m.collection_id == collection.id])
    return render(request, 'studio/collections.html', {'nav': 'collections', 'collections': collections, 'archived': archived})

@login_required
def collection_detail(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    items = enrich(base_models().filter(collection=collection))
    figures = totals(items)
    figures['balance'] = collection.budget - figures['actual']
    return render(request, 'studio/collection_detail.html', {'nav': 'collections', 'collection': collection, 'models': items, 'figures': figures})

@staff_required
def collection_form(request, pk=None):
    instance = get_object_or_404(Collection, pk=pk) if pk else None
    form = CollectionForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            saved = form.save()
            audit(request.user, 'collection.saved', f'Colección guardada: {saved.name}', details={'collection_id': saved.id, 'budget': str(saved.budget)})
        messages.success(request, 'Colección guardada.')
        return redirect('collection_detail', pk=saved.pk)
    return render(request, 'studio/form.html', {'nav': 'collections', 'form': form, 'title': 'Editar colección' if pk else 'Nueva colección', 'subtitle': 'Define el presupuesto y la fecha objetivo. Después añade tus modelos.', 'back': reverse('collection_detail', args=[pk]) if pk else reverse('collection_list')})

@login_required
def garment_list(request):
    collections, selected = selected_collection(request, include_archived=True)
    archived = request.GET.get('archived') == '1'
    query = base_models().filter(archived=archived)
    if selected:
        query = query.filter(collection=selected)
    search = request.GET.get('q', '').strip()
    if search:
        from django.db.models import Q
        query = query.filter(Q(code__icontains=search) | Q(name__icontains=search) | Q(workshop__icontains=search))
    models = enrich(query)
    status = request.GET.get('status', '')
    if status == 'over':
        models = [m for m in models if m.summary['over_budget']]
    elif status == 'overdue':
        models = [m for m in models if m.summary['overdue']]
    elif status:
        models = [m for m in models if m.summary['stage_key'] == status]
    return render(request, 'studio/models.html', {'nav': 'models', 'models': models, 'collections': collections, 'selected': selected, 'search': search, 'status': status, 'archived': archived})

@staff_required
def garment_form(request, pk=None):
    instance = get_object_or_404(Garment, pk=pk) if pk else None
    initial = {'collection': request.GET.get('collection')} if request.GET.get('collection', '').isdigit() else {}
    if request.method == 'POST':
        try:
            with transaction.atomic():
                instance = lock_model(pk) if pk else None
                form = GarmentForm(request.POST, instance=instance)
                if form.is_valid():
                    saved = form.save()
                    check_amounts(saved)
                    audit(request.user, 'model.saved', f'Modelo guardado: {saved.code}', saved, {'units': saved.planned_units})
                    messages.success(request, 'Modelo guardado. Los cambios en el plan requieren una nueva aprobación para afectar la producción.')
                    return redirect('garment_detail', pk=saved.pk)
        except ValidationError as error:
            form.add_error(None, error)
    else:
        form = GarmentForm(instance=instance, initial=initial)
    return render(request, 'studio/form.html', {'nav': 'models', 'form': form, 'title': 'Editar modelo' if pk else 'Nuevo modelo', 'subtitle': 'Comienza con las cantidades y el taller. Luego añade los costos por prenda o por lote.', 'back': reverse('garment_detail', args=[pk]) if pk else reverse('garment_list')})

@login_required
def garment_detail(request, pk):
    garment = get_object_or_404(base_models(), pk=pk)
    summary = summarize(garment)
    lines = list(garment.budget_lines.all())
    for line in lines:
        line.total = line_total(line, garment.planned_units)
        line.per_garment = money(line.total / garment.planned_units)
    categories = []
    for key, label in CATEGORIES:
        estimate = sum((l.total for l in lines if l.category == key), ZERO)
        actual = sum((e.amount for e in garment.expenses.all() if e.category == key and not e.voided), ZERO)
        if estimate or actual:
            categories.append({'label': label, 'planned': estimate, 'actual': actual, 'delta': estimate - actual})
    return render(request, 'studio/model_detail.html', {'nav': 'models', 'garment': garment, 's': summary, 'lines': lines, 'categories': categories, 'expenses': garment.expenses.all(), 'events': garment.events.all(), 'audits': garment.audit_set.select_related('user')[:15]})

@staff_required
def budget_line_form(request, pk, line_id=None):
    garment = get_object_or_404(Garment.objects.select_related('collection'), pk=pk)
    instance = get_object_or_404(BudgetLine, pk=line_id, garment=garment) if line_id else BudgetLine(garment=garment)
    form = BudgetLineForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                locked = lock_model(pk)
                check_active(locked)
                old = snapshot(locked)
                form.save()
                check_amounts(locked)
                audit(request.user, 'budget.edited', f'Plan de costos actualizado: {garment.code}', locked, {'previous': old, 'current': snapshot(locked)})
            messages.success(request, 'Concepto guardado. La aprobación anterior se conserva hasta aprobar el plan de nuevo.')
            return redirect(reverse('garment_detail', args=[pk]) + '#presupuesto')
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, 'studio/form.html', {'nav': 'models', 'form': form, 'title': 'Editar concepto' if line_id else 'Añadir costo previsto', 'subtitle': str(garment), 'back': reverse('garment_detail', args=[pk]), 'budget_calculator': True, 'planned_units': garment.planned_units})

@staff_required
@require_POST
def delete_budget_line(request, pk, line_id):
    line = get_object_or_404(BudgetLine, pk=line_id, garment_id=pk)
    try:
        with transaction.atomic():
            garment = lock_model(pk)
            check_active(garment)
            old = snapshot(garment)
            line.delete()
            audit(request.user, 'budget.edited', f'Concepto retirado del plan: {garment.code}', garment, {'previous': old, 'current': snapshot(garment)})
        messages.success(request, 'Concepto retirado del plan. El presupuesto aprobado conserva su versión anterior.')
    except ValidationError as error:
        errors_to_messages(request, error)
    return redirect(reverse('garment_detail', args=[pk]) + '#presupuesto')

@staff_required
@require_POST
def approve(request, pk):
    get_object_or_404(Garment, pk=pk)
    try:
        approve_budget(pk, request.user, request.POST.get('allow_overbudget') == 'on')
        messages.success(request, 'Presupuesto y unidades aprobados. Ya puedes registrar producción.')
    except ValidationError as error:
        errors_to_messages(request, error)
    return redirect('garment_detail', pk=pk)

@staff_required
@require_POST
def archive(request, entity, pk):
    model = {'modelo': Garment, 'coleccion': Collection}.get(entity)
    if model is None:
        raise Http404
    obj = get_object_or_404(model, pk=pk)
    with transaction.atomic():
        if model is Garment:
            obj = lock_model(pk)
        else:
            obj = Collection.objects.select_for_update().get(pk=pk)
        obj.archived = not obj.archived
        obj.save(update_fields=['archived'])
        audit(request.user, 'record.archived', f'{"Archivado" if obj.archived else "Reactivado"}: {obj}', obj if model is Garment else None, {'archived': obj.archived, 'id': pk})
    messages.success(request, 'Registro archivado; su historial y costos se conservan.' if obj.archived else 'Registro reactivado.')
    return redirect('garment_detail' if model is Garment else 'collection_detail', pk=pk)

@login_required
def expense_form(request):
    return operation_form(request, ExpenseForm, record_expense, 'Registrar costo real', 'Registra el costo atribuible a este modelo. Una compra para stock general todavía no es consumo de este modelo.', 'expenses')

@login_required
def production_form(request):
    return operation_form(request, ProductionForm, record_event, 'Registrar avance', 'Registra las unidades adicionales que completaron una etapa, sin repetir las ya registradas.', 'models')

def operation_form(request, form_class, record, title, subtitle, nav):
    model_id = request.GET.get('modelo', '')
    initial = {'garment': model_id} if model_id.isdigit() else {}
    form = form_class(request.POST or None, initial=initial)
    context_model = Garment.objects.filter(pk=model_id).first() if model_id.isdigit() else None
    if context_model:
        context_model.summary = summarize(context_model)
    if request.method == 'POST' and form.is_valid():
        cleaned = dict(form.cleaned_data)
        garment = cleaned.pop('garment')
        token = cleaned.pop('token')
        try:
            result, created = record(garment.pk, request.user, cleaned, token)
            messages.success(request, 'Operación registrada.' if created else 'Esta operación ya estaba registrada; no se duplicó.')
            return redirect(reverse('garment_detail', args=[garment.pk]) + ('#gastos' if form_class is ExpenseForm else '#produccion'))
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, 'studio/form.html', {'nav': nav, 'form': form, 'title': title, 'subtitle': subtitle, 'back': reverse('garment_detail', args=[model_id]) if context_model else reverse('dashboard'), 'context_model': context_model, 'production_help': form_class is ProductionForm})

@login_required
def expense_list(request):
    collections, selected = selected_collection(request, include_archived=True)
    query = Expense.objects.select_related('garment__collection', 'created_by')
    if selected:
        query = query.filter(garment__collection=selected)
    category = request.GET.get('category', '')
    if category in dict(CATEGORIES):
        query = query.filter(category=category)
    if request.GET.get('q'):
        from django.db.models import Q
        query = query.filter(Q(description__icontains=request.GET['q']) | Q(garment__code__icontains=request.GET['q']) | Q(reference__icontains=request.GET['q']))
    active = list(query.filter(voided=False))
    return render(request, 'studio/expenses.html', {'nav': 'expenses', 'page': Paginator(query, 30).get_page(request.GET.get('page')), 'collections': collections, 'selected': selected, 'categories': CATEGORIES, 'category': category, 'amount': sum((e.amount for e in active), ZERO), 'paid': sum((e.paid_amount for e in active), ZERO)})

@login_required
def paid_form(request, pk):
    expense = get_object_or_404(Expense.objects.select_related('garment'), pk=pk)
    form = PaidForm(request.POST or None, initial={'paid_amount': expense.paid_amount})
    if request.method == 'POST' and form.is_valid():
        try:
            set_paid(pk, request.user, form.cleaned_data['paid_amount'])
            messages.success(request, 'Total pagado actualizado sin crear otro costo.')
            return redirect(reverse('garment_detail', args=[expense.garment_id]) + '#gastos')
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, 'studio/form.html', {'nav': 'expenses', 'form': form, 'title': 'Actualizar pago acumulado', 'subtitle': f'{expense.description} · costo total S/ {expense.amount}. Indica cuánto has pagado en total, no un pago adicional.', 'back': reverse('garment_detail', args=[expense.garment_id])})

@staff_required
def void_form(request, entity, pk):
    model = {'gasto': Expense, 'avance': ProductionEvent}.get(entity)
    if model is None:
        raise Http404
    record = get_object_or_404(model.objects.select_related('garment'), pk=pk)
    form = VoidForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            void_record(model, pk, request.user, form.cleaned_data['reason'])
            messages.success(request, 'Registro anulado. El original y su motivo permanecen en el historial.')
            return redirect('garment_detail', pk=record.garment_id)
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, 'studio/form.html', {'nav': 'models', 'form': form, 'title': 'Anular registro incorrecto', 'subtitle': f'{record.garment}. Esta acción corrige un registro; no representa un reembolso de dinero. Las etapas dependientes deben corregirse primero.', 'back': reverse('garment_detail', args=[record.garment_id]), 'submit_label': 'Anular registro', 'danger': True})

@login_required
def activity(request):
    query = Audit.objects.select_related('user', 'garment')
    return render(request, 'studio/activity.html', {'nav': 'activity', 'page': Paginator(query, 40).get_page(request.GET.get('page'))})

@login_required
def guide(request):
    return render(request, 'studio/guide.html', {'nav': 'guide'})

@require_POST
def demo_login(request):
    if not settings.DEMO_MODE:
        raise Http404
    user = get_user_model().objects.filter(username='demo', is_active=True).first()
    if not user:
        messages.error(request, 'El modo demo aún no tiene datos. Ejecuta seed_demo en la base de demostración.')
        return redirect('login')
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('dashboard')

def csv_safe(value):
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value

@login_required
def export_csv(request, entity):
    _, selected = selected_collection(request, include_archived=True)
    output = io.StringIO()
    writer = csv.writer(output)
    def row(values):
        writer.writerow([csv_safe(x) for x in values])
    if entity == 'modelos':
        query = base_models()
        if selected:
            query = query.filter(collection=selected)
        row(['ID', 'Colección', 'Código', 'Modelo', 'Unidades previstas', 'Unidades aprobadas', 'Aprobadas por calidad', 'Rechazadas', 'Plan actual PEN', 'Presupuesto aprobado PEN', 'Costo registrado PEN', 'Pagado PEN', 'Costo por unidad plan PEN', 'Costo por unidad aprobada PEN', 'Estado', 'Archivado'])
        for model in enrich(query):
            s = model.summary
            row([model.pk, model.collection.name, model.code, model.name, model.planned_units, model.approved_units, s['good'], s['counts']['rejected'], s['planned'], model.approved_budget if model.approved_budget is not None else '', s['actual'], s['paid'], s['planned_unit'], s['actual_unit'], s['status'], model.archived])
    elif entity in ('gastos', 'avances'):
        query = (Expense if entity == 'gastos' else ProductionEvent).objects.select_related('garment__collection', 'created_by')
        if selected:
            query = query.filter(garment__collection=selected)
        if entity == 'gastos':
            row(['ID', 'Fecha', 'Colección', 'Modelo', 'Categoría', 'Concepto', 'Costo PEN', 'Pagado PEN', 'Proveedor', 'Referencia', 'Anulado', 'Motivo', 'Usuario'])
            for e in query:
                row([e.pk, e.date, e.garment.collection.name, e.garment.code, e.get_category_display(), e.description, e.amount, e.paid_amount, e.supplier, e.reference, e.voided, e.void_reason, e.created_by.username])
        else:
            row(['ID', 'Fecha', 'Colección', 'Modelo', 'Etapa', 'Unidades', 'Notas', 'Anulado', 'Motivo', 'Usuario'])
            for e in query:
                row([e.pk, e.date, e.garment.collection.name, e.garment.code, e.get_stage_display(), e.quantity, e.notes, e.voided, e.void_reason, e.created_by.username])
    else:
        raise Http404
    response = HttpResponse('\ufeff' + output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="maryruss-{entity}-{timezone.localdate()}.csv"'
    return response

@staff_required
def backup_download(request):
    from .backup import create_backup
    payload = create_backup()
    audit(request.user, 'backup.created', 'Respaldo completo descargado')
    response = HttpResponse(payload, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="maryruss-respaldo-{timezone.localtime():%Y%m%d-%H%M%S}.zip"'
    response['Cache-Control'] = 'no-store'
    return response
