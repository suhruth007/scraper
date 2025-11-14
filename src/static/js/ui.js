document.addEventListener('DOMContentLoaded', function() {
  const btn = document.getElementById('mode-toggle');
  if (btn) {
    btn.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
    });
  }

  const form = document.getElementById('uploadForm');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = new FormData(form);
      const res = await fetch(form.action, {
        method: 'POST',
        body: data
      });
      const json = await res.json();
      if (res.status === 202) {
        toast('Scan started — check dashboard soon', 'success');
      } else {
        toast(json.error || 'Error starting scan', 'error');
      }
    });
  }
});
