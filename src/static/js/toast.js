function toast(message, level='info') {
  const el = document.createElement('div');
  el.textContent = message;
  el.className = "fixed right-4 bottom-6 px-4 py-2 rounded shadow text-white";
  el.style.zIndex = 9999;
  if (level === 'success') el.style.background = '#16a34a';
  else if (level === 'error') el.style.background = '#dc2626';
  else el.style.background = '#334155';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
