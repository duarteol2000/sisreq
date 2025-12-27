// Inicializa DataTables em tabelas com a classe ".js-datatable"
function initDataTables(context) {
  const tables = (context || document).querySelectorAll('.js-datatable');
  tables.forEach((table) => {
    if (!table.dataset.dtInitialized) {
      $(table).DataTable({
        paging: true,
        searching: true,
        info: true,
        ordering: true,
        language: {
          url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json',
        },
      });
      table.dataset.dtInitialized = 'true';
    }
  });
}

document.addEventListener('DOMContentLoaded', () => initDataTables());

// HTMX helpers para modal e atualização de grids
document.body.addEventListener('htmx:afterSwap', (event) => {
  if (event.detail.target.id === 'modalContainer') {
    const modalEl = document.querySelector('#modalContainer .modal');
    if (modalEl) {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
      modalEl.addEventListener('hidden.bs.modal', () => {
        document.getElementById('modalContainer').innerHTML = '';
      });
    }
  }
  if (event.detail.target.id === 'materiais-grid') {
    initDataTables(event.detail.target);
  }
});

// Eventos disparados via HX-Trigger
document.body.addEventListener('showToast', (event) => {
  const detail = event.detail || {};
  const level = detail.level || 'info';
  const message = detail.message || '';
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-bg-${level === 'error' ? 'danger' : level} border-0`;
  toast.role = 'alert';
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
    </div>`;
  document.body.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
  bsToast.show();
  toast.addEventListener('hidden.bs.toast', () => toast.remove());
});

document.body.addEventListener('closeModal', () => {
  const modalEl = document.querySelector('#modalContainer .modal.show');
  if (modalEl) {
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();
  }
});

document.body.addEventListener('refresh-materials', () => {
  const grid = document.getElementById('materiais-grid');
  if (grid) {
    htmx.ajax('GET', grid.dataset.refreshUrl || window.location.href, { target: '#materiais-grid', swap: 'outerHTML' });
  }
});
