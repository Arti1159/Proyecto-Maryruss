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
const calculator = document.querySelector('[data-budget-units]');
if (calculator) {
  const quantity = calculator.querySelector('[name="quantity"]');
  const price = calculator.querySelector('[name="unit_price"]');
  const basis = calculator.querySelector('[name="basis"]');
  const preview = document.getElementById('budget-preview');
  const currency = new Intl.NumberFormat('es-PE', {style:'currency', currency:'PEN'});
  const update = () => {
    const count = Number(quantity.value), amount = Number(price.value), units = Number(calculator.dataset.budgetUnits);
    if (!quantity.value || !price.value || count <= 0 || amount < 0 || !Number.isFinite(count * amount * units)) {
      preview.textContent = 'Completa cantidad y precio'; return;
    }
    const total = count * amount * (basis.value === 'unit' ? units : 1);
    preview.textContent = `${currency.format(total / units)} / prenda · ${currency.format(total)} total`;
  };
  [quantity, price, basis].forEach(input => input.addEventListener('input', update)); update();
}
