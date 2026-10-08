'use strict';
const toggle = document.getElementById('menu-toggle');
if (toggle) {
  toggle.addEventListener('click', () => {
    const opened = document.body.classList.toggle('sidebar-open');
    toggle.setAttribute('aria-expanded', String(opened));
  });
  document.addEventListener('click', event => {
    if (document.body.classList.contains('sidebar-open') && !event.target.closest('#sidebar') && !event.target.closest('#menu-toggle')) {
      document.body.classList.remove('sidebar-open'); toggle.setAttribute('aria-expanded', 'false');
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { document.body.classList.remove('sidebar-open'); toggle.setAttribute('aria-expanded', 'false'); }
  });
}
document.querySelectorAll('[data-auto-submit]').forEach(select => select.addEventListener('change', () => select.form.requestSubmit()));
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', event => {
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
    if (form.dataset.submitting === 'true') { event.preventDefault(); return; }
    form.dataset.submitting = 'true';
    form.querySelectorAll('button[type="submit"]').forEach(button => {
      button.disabled = true; button.dataset.originalLabel = button.textContent; button.textContent = 'Guardando…';
    });
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('form').forEach(form => { delete form.dataset.submitting; });
  document.querySelectorAll('button[data-original-label]').forEach(button => { button.disabled = false; button.textContent = button.dataset.originalLabel; });
});
// Categories can be added in another tab without losing a partially filled form.
document.querySelectorAll('[data-category-options-url]').forEach(select => {
  const field = select.closest('.field');
  const button = field.querySelector('.refresh-categories');
  const status = field.querySelector('.category-refresh-status');
  if (!button) return;
  button.addEventListener('click', async () => {
    button.disabled = true; status.textContent = 'Actualizando…';
    try {
      const response = await fetch(select.dataset.categoryOptionsUrl, {headers: {'Accept': 'application/json'}});
      if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('Unavailable');
      const data = await response.json();
      const selected = select.value;
      const old = Array.from(select.options).find(option => option.value === selected);
      select.replaceChildren(new Option('Elige una categoría de gasto', ''));
      data.categories.forEach(category => select.add(new Option(category.name, category.code)));
      if (old && selected === select.dataset.existingCategory && !data.categories.some(category => category.code === selected)) {
        select.add(new Option(old.textContent.replace(/ \(archivada\)$/, '') + ' (archivada)', selected));
      }
      select.value = selected;
      status.textContent = selected && !select.value ? 'La categoría elegida se archivó. Elige otra activa.' : 'Lista actualizada.';
    } catch (_) { status.textContent = 'No se pudo actualizar. Revisa tu conexión y tu sesión e inténtalo de nuevo.'; }
    finally { button.disabled = false; }
  });
});
const calculator = document.querySelector('[data-budget-units]');
if (calculator) {
  const quantity = calculator.querySelector('[name="quantity"]');
  const price = calculator.querySelector('[name="unit_price"]');
  const basis = calculator.querySelector('[name="basis"]');
  const unit = calculator.querySelector('[name="unit"]');
  const preview = document.getElementById('budget-preview');
  const perUnit = document.getElementById('budget-unit-preview');
  const formula = document.getElementById('budget-formula');
  const currency = new Intl.NumberFormat('es-PE', {style:'currency', currency:'PEN'});
  const rateCurrency = new Intl.NumberFormat('es-PE', {style:'currency', currency:'PEN', minimumFractionDigits:2, maximumFractionDigits:4});
  const number = new Intl.NumberFormat('es-PE', {maximumFractionDigits:4});
  const units = BigInt(calculator.dataset.budgetUnits);
  // Match server Decimal calculations: 4 decimal places for inputs, half-up cents.
  const scaled = value => {
    if (value.startsWith('.')) value = '0' + value;
    if (value.endsWith('.')) value += '0';
    if (!/^\d+(?:\.\d{1,4})?$/.test(value)) return null;
    const [integer, decimals = ''] = value.split('.');
    return BigInt(integer) * 10000n + BigInt(decimals.padEnd(4, '0'));
  };
  const update = () => {
    const batch = basis.value === 'batch';
    const measure = unit.value.trim() || 'unidad';
    calculator.querySelector('[data-field-label="quantity"]').textContent = batch ? 'Cantidad total para este costo' : 'Cantidad que usa una prenda';
    calculator.querySelector('[data-field-label="unit_price"]').textContent = `Precio por ${measure} (S/)`;
    ['quantity', 'unit_price'].forEach(name => {
      const label = calculator.querySelector(`[data-field-label="${name}"]`);
      label.closest('.field-label').querySelector('summary').setAttribute('aria-label', `Información sobre ${label.textContent}`);
    });
    document.getElementById('id_quantity_help').textContent = batch ? 'Cantidad para todo el lote. Ej.: 1 servicio de transporte o 600 metros comprados para este modelo.' : 'Consumo de UNA prenda. Ej.: 1.2 metros de tela o 1 servicio de confección por prenda.';
    const count = scaled(quantity.value), amount = scaled(price.value);
    if (count === null || amount === null || count <= 0n || units <= 0n) {
      preview.textContent = 'Completa cantidad y precio'; perUnit.textContent = '—';
      formula.textContent = 'Usa una cantidad mayor que cero y un precio desde cero, con hasta 4 decimales.'; return;
    }
    const cents = (count * amount * (batch ? 1n : units) * 100n + 50000000n) / 100000000n;
    if (cents > 999999999999n) {
      preview.textContent = 'El importe supera el límite'; perUnit.textContent = '—';
      formula.textContent = 'Revisa la cantidad y el precio antes de guardar.'; return;
    }
    const eachCents = (cents * 2n + units) / (units * 2n);
    preview.textContent = currency.format(Number(cents) / 100);
    perUnit.textContent = currency.format(Number(eachCents) / 100);
    formula.textContent = `${number.format(Number(count) / 10000)} ${measure} × ${rateCurrency.format(Number(amount) / 10000)} por ${measure}${batch ? ' = costo de todo el lote. Se divide entre ' + units + ' prendas para calcular el costo por prenda.' : ' × ' + units + ' prendas = costo total del modelo.'}`;
  };
  [quantity, price, basis, unit].forEach(input => input.addEventListener('input', update)); update();
}
