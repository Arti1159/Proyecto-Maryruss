from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Audit, BudgetLine, Expense, Garment, ProductionEvent, STAGES

ZERO = Decimal('0.00')
MAX_MONEY = Decimal('9999999999.99')

def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def line_total(line, units):
    return money(line.quantity * line.unit_price * (units if line.basis == 'unit' else 1))

def snapshot(garment):
    lines = list(garment.budget_lines.all())
    return {
        'units': garment.planned_units,
        'lines': [{'id': l.id, 'category': l.category_id, 'description': l.description, 'basis': l.basis,
                   'quantity': str(l.quantity), 'unit': l.unit, 'unit_price': str(l.unit_price)} for l in lines],
        'total': str(sum((line_total(l, garment.planned_units) for l in lines), ZERO)),
    }

def summarize(garment):
    plan = snapshot(garment)
    planned = Decimal(plan['total'])
    expenses = [e for e in garment.expenses.all() if not e.voided]
    actual = sum((e.amount for e in expenses), ZERO)
    paid = sum((e.paid_amount for e in expenses), ZERO)
    counts = {key: 0 for key, _ in STAGES}
    for event in garment.events.all():
        if not event.voided:
            counts[event.stage] += event.quantity
    baseline = garment.approved_budget if garment.approved_budget is not None else planned
    units = garment.approved_units if garment.approved_budget is not None else garment.planned_units
    good = counts['approved']
    done = good + counts['rejected']
    status = 'Por iniciar'
    stage_key = 'pending'
    if done >= units and units:
        status = 'Finalizado' if not counts['rejected'] else 'Finalizado con rechazos'
        stage_key = 'done'
    elif counts['finishing']:
        status, stage_key = 'Control de calidad', 'quality'
    elif counts['sewing']:
        status, stage_key = 'Acabados', 'finishing'
    elif counts['cut']:
        status, stage_key = 'En confección', 'sewing'
    changed = bool(garment.approved_snapshot and plan != garment.approved_snapshot)
    deadline = garment.due_date or garment.collection.due_date
    overdue = bool(deadline and deadline < timezone.localdate() and done < units and not garment.archived)
    bands = [
        ('Por cortar', max(units - counts['cut'], 0), 'pending'),
        ('En confección', counts['cut'] - counts['sewing'], 'cut'),
        ('En acabados', counts['sewing'] - counts['finishing'], 'sewing'),
        ('En calidad', counts['finishing'] - good - counts['rejected'], 'finishing'),
        ('Aprobadas', good, 'approved'), ('Rechazadas', counts['rejected'], 'rejected'),
    ]
    return {
        'planned': planned, 'planned_unit': money(planned / garment.planned_units),
        'baseline': baseline, 'baseline_unit': money(baseline / units) if units else None,
        'actual': actual, 'paid': paid, 'unpaid': actual - paid,
        'actual_unit': money(actual / units) if units else None,
        'good_unit': money(actual / good) if good else None,
        'balance': baseline - actual, 'over_budget': actual > baseline,
        'counts': counts, 'units': units, 'good': good, 'done': done,
        'progress': round(100 * good / units) if units else 0,
        'spent_pct': min(round(100 * actual / baseline), 100) if baseline else (100 if actual else 0),
        'status': status, 'stage_key': stage_key, 'changed': changed, 'overdue': overdue,
        'bands': [{'label': label, 'quantity': qty, 'key': key, 'pct': 100 * qty / units if units else 0} for label, qty, key in bands],
    }

def enrich(garments):
    items = list(garments)
    for item in items:
        item.summary = summarize(item)
    return items

def audit(user, action, description, garment=None, details=None):
    return Audit.objects.create(user=user, action=action, description=description,
                                garment=garment, details=details or {})

def lock_model(pk):
    # The first write also serializes SQLite writers. PostgreSQL locks the same row.
    Garment.objects.filter(pk=pk).update(version=F('version') + 1)
    return Garment.objects.select_for_update().select_related('collection').get(pk=pk)

def check_active(garment):
    if garment.archived or garment.collection.archived:
        raise ValidationError('El modelo o la colección están archivados. Reactívalos para registrar operaciones.')

def check_amounts(garment):
    if Decimal(snapshot(garment)['total']) > MAX_MONEY:
        raise ValidationError('El presupuesto supera el importe máximo permitido.')

@transaction.atomic
def approve_budget(pk, user, allow_overbudget=False):
    garment = lock_model(pk)
    check_active(garment)
    plan = snapshot(garment)
    if not plan['lines']:
        raise ValidationError('Añade al menos un concepto al presupuesto antes de aprobarlo.')
    check_amounts(garment)
    counts = summarize(garment)['counts']
    if garment.planned_units < counts['cut']:
        raise ValidationError('El nuevo plan no puede ser menor que las unidades ya cortadas.')
    other_approved = sum((x.approved_budget or ZERO for x in Garment.objects.filter(collection=garment.collection).exclude(pk=pk)), ZERO)
    if other_approved + Decimal(plan['total']) > garment.collection.budget and not allow_overbudget:
        raise ValidationError('La suma de presupuestos aprobados supera el presupuesto de la colección. Marca la autorización de exceso si deseas continuar.')
    if garment.approved_snapshot == plan:
        return garment
    old = garment.approved_snapshot
    garment.approved_snapshot = plan
    garment.approved_budget = Decimal(plan['total'])
    garment.approved_units = garment.planned_units
    garment.approved_at = timezone.now()
    garment.save(update_fields=['approved_snapshot', 'approved_budget', 'approved_units', 'approved_at'])
    audit(user, 'budget.approved', f'Presupuesto aprobado para {garment.code}', garment, {'previous': old, 'approved': plan})
    return garment

def validate_counts(counts, units):
    if not (0 <= counts['cut'] <= units):
        raise ValidationError('El corte no puede superar las unidades aprobadas.')
    if not (0 <= counts['sewing'] <= counts['cut']):
        raise ValidationError('No puedes confeccionar más unidades de las que han pasado por corte.')
    if not (0 <= counts['finishing'] <= counts['sewing']):
        raise ValidationError('No puedes terminar más unidades de las confeccionadas.')
    if counts['approved'] < 0 or counts['rejected'] < 0 or counts['approved'] + counts['rejected'] > counts['finishing']:
        raise ValidationError('La suma de aprobadas y rechazadas no puede superar las unidades con acabados.')

@transaction.atomic
def record_event(pk, user, cleaned, token):
    garment = lock_model(pk)
    existing = ProductionEvent.objects.filter(token=token).first()
    if existing:
        if existing.garment_id != pk:
            raise ValidationError('La referencia ya se usó para otro modelo.')
        return existing, False
    check_active(garment)
    if garment.approved_budget is None:
        raise ValidationError('Aprueba el presupuesto y las unidades antes de registrar producción.')
    event = ProductionEvent(garment=garment, created_by=user, token=token, **cleaned)
    event.full_clean()
    if event.date > timezone.localdate():
        raise ValidationError('Un avance realizado no puede tener fecha futura.')
    counts = summarize(garment)['counts']
    counts[event.stage] += event.quantity
    validate_counts(counts, garment.approved_units)
    event.save()
    audit(user, 'production.recorded', f'{garment.code}: {event.quantity} en {event.get_stage_display()}', garment, {'event_id': event.id})
    return event, True

@transaction.atomic
def record_expense(pk, user, cleaned, token):
    garment = lock_model(pk)
    existing = Expense.objects.filter(token=token).first()
    if existing:
        if existing.garment_id != pk:
            raise ValidationError('La referencia ya se usó para otro modelo.')
        return existing, False
    check_active(garment)
    cleaned = dict(cleaned)
    if isinstance(cleaned.get('category'), str):
        cleaned['category_id'] = cleaned.pop('category')
    expense = Expense(garment=garment, created_by=user, token=token, **cleaned)
    expense.full_clean()
    if expense.date > timezone.localdate():
        raise ValidationError('Un costo registrado no puede tener fecha futura.')
    expense.save()
    audit(user, 'expense.recorded', f'{garment.code}: {expense.description}', garment,
          {'expense_id': expense.id, 'amount': str(expense.amount), 'paid': str(expense.paid_amount)})
    return expense, True

@transaction.atomic
def void_record(model, pk, user, reason):
    if not reason.strip():
        raise ValidationError('Explica el motivo de la anulación.')
    if len(reason) > 240:
        raise ValidationError('El motivo admite hasta 240 caracteres.')
    original = model.objects.get(pk=pk)
    garment = lock_model(original.garment_id)
    original.refresh_from_db()
    if original.voided:
        return
    if model is ProductionEvent:
        counts = summarize(garment)['counts']
        counts[original.stage] -= original.quantity
        validate_counts(counts, garment.approved_units)
    original.voided = True
    original.void_reason = reason.strip()
    original.save(update_fields=['voided', 'void_reason'])
    audit(user, 'record.voided', f'Anulación en {garment.code}: {reason}', garment,
          {'type': model.__name__, 'record_id': pk})

@transaction.atomic
def set_paid(pk, user, amount):
    expense = Expense.objects.get(pk=pk)
    garment = lock_model(expense.garment_id)
    expense.refresh_from_db()
    if expense.voided:
        raise ValidationError('No puedes modificar un registro anulado.')
    previous = expense.paid_amount
    expense.paid_amount = amount
    expense.full_clean()
    expense.save(update_fields=['paid_amount'])
    if previous != amount:
        audit(user, 'payment.updated', f'Pago acumulado actualizado: {expense.description}', garment,
              {'expense_id': expense.id, 'previous': str(previous), 'paid': str(amount)})
