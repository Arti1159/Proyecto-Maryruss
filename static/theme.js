/* Runs in the head, before CSS, so the saved theme is applied before painting. */
(() => {
  'use strict';
  const key = 'maryruss-theme';
  const modes = ['system', 'light', 'dark'];
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let mode = 'system';
  try { const saved = localStorage.getItem(key); if (modes.includes(saved)) mode = saved; } catch (_) { /* Theme still works when storage is unavailable. */ }
  const apply = () => {
    const resolved = mode === 'system' ? (media.matches ? 'dark' : 'light') : mode;
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
    document.querySelectorAll('[data-theme-selector]').forEach(select => { select.value = mode; });
  };
  apply();
  media.addEventListener('change', apply);
  window.addEventListener('storage', event => {
    if (event.key === key) { mode = modes.includes(event.newValue) ? event.newValue : 'system'; apply(); }
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    document.querySelectorAll('[data-theme-selector]').forEach(select => select.addEventListener('change', () => {
      mode = select.value;
      try { localStorage.setItem(key, mode); } catch (_) { /* Use in-memory preference. */ }
      apply();
    }));
  });
})();
