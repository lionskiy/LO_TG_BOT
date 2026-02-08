/**
 * Admin «Работа с БД»: employees table, three views, cell edit, import.
 * GET /api/hr/employees?view=..., PATCH /api/hr/employees/:id, POST /api/hr/import
 */

const DB_COLUMNS = [
  'id', 'personal_number', 'full_name', 'email', 'jira_worker_id', 'position', 'mvz', 'supervisor',
  'hire_date', 'fte', 'dismissal_date', 'birth_date', 'mattermost_username',
  'is_supervisor', 'is_delivery_manager', 'team', 'created_at', 'updated_at'
];

const DB_EDITABLE = new Set(['fte', 'dismissal_date', 'is_supervisor', 'is_delivery_manager', 'team', 'mvz', 'supervisor', 'position', 'mattermost_username']);

let currentDbView = 'all';

function getHeaders() {
  const key = document.getElementById('adminKey').value.trim();
  const headers = { 'Content-Type': 'application/json' };
  if (key) headers['X-Admin-Key'] = key;
  return headers;
}

async function api(path, options = {}) {
  const res = await fetch(path, { ...options, headers: { ...getHeaders(), ...(options.headers || {}) } });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

async function loadDbEmployees() {
  const thead = document.getElementById('dbTableHead');
  const tbody = document.getElementById('dbTableBody');
  const placeholder = document.getElementById('dbPlaceholder');
  if (!thead || !tbody || !placeholder) return;
  thead.innerHTML = '';
  tbody.innerHTML = '';
  placeholder.hidden = true;
  try {
    const list = await api(`/api/hr/employees?view=${currentDbView}`);
    if (!Array.isArray(list)) throw new Error('Invalid response');
    const cols = DB_COLUMNS;
    const tr = document.createElement('tr');
    cols.forEach(c => {
      const th = document.createElement('th');
      th.textContent = c;
      th.scope = 'col';
      tr.appendChild(th);
    });
    thead.appendChild(tr);
    list.forEach(row => {
      const tr = document.createElement('tr');
      tr.dataset.id = String(row.id);
      cols.forEach(col => {
        const td = document.createElement('td');
        const val = row[col];
        const isEditable = DB_EDITABLE.has(col);
        if (isEditable) {
          td.className = 'db-cell-editable';
          td.tabIndex = 0;
          td.dataset.field = col;
          if (typeof val === 'boolean') {
            td.textContent = val ? 'да' : 'нет';
          } else {
            td.textContent = val != null ? String(val) : '';
          }
          td.addEventListener('click', () => startEditCell(td, row));
        } else {
          td.textContent = val != null ? String(val) : '';
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    if (list.length === 0) placeholder.hidden = false;
  } catch (e) {
    placeholder.hidden = false;
    placeholder.textContent = 'Ошибка загрузки: ' + e.message;
    showToast('Ошибка загрузки списка: ' + e.message, 'error');
  }
}

function startEditCell(td, row) {
  const field = td.dataset.field;
  const id = row.id;
  const current = row[field];
  const isBool = typeof current === 'boolean';
  if (isBool) {
    const newVal = !current;
    saveDbCell(id, field, newVal).then(() => {
      row[field] = newVal;
      td.textContent = newVal ? 'да' : 'нет';
      showToast('Сохранено', 'success');
    }).catch(e => showToast('Ошибка: ' + e.message, 'error'));
    return;
  }
  const input = document.createElement('input');
  input.type = 'text';
  input.value = current != null ? String(current) : '';
  input.className = 'db-cell-input';
  td.textContent = '';
  td.appendChild(input);
  input.focus();
  const commit = () => {
    const val = input.value.trim();
    td.removeChild(input);
    td.textContent = val || '';
    td.classList.remove('db-cell--editing');
    if (String(current) !== val) {
      let payload = val;
      if (field === 'fte') payload = parseFloat(val) || 1;
      saveDbCell(id, field, payload).then(() => {
        row[field] = payload;
        showToast('Сохранено', 'success');
      }).catch(e => showToast('Ошибка: ' + e.message, 'error'));
    }
  };
  td.classList.add('db-cell--editing');
  input.addEventListener('blur', commit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') commit();
    if (e.key === 'Escape') {
      td.removeChild(input);
      td.textContent = current != null ? String(current) : '';
      td.classList.remove('db-cell--editing');
    }
  });
}

async function saveDbCell(id, field, value) {
  await api(`/api/hr/employees/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ [field]: value }),
  });
}

async function doDbImport(file) {
  const resultEl = document.getElementById('dbImportResult');
  if (!resultEl) return;
  resultEl.hidden = false;
  resultEl.textContent = 'Загрузка...';
  resultEl.className = 'db-import-result';
  const formData = new FormData();
  formData.append('file', file);
  const headers = getHeaders();
  delete headers['Content-Type'];
  try {
    const res = await fetch('/api/hr/import', { method: 'POST', headers, body: formData });
    let data = {};
    try {
      const text = await res.text();
      if (text) data = JSON.parse(text);
    } catch (_) {}
    if (!res.ok) {
      resultEl.textContent = (data.detail || data.message || res.statusText);
      resultEl.classList.add('db-import-result--error');
      showToast('Ошибка импорта', 'error');
      return;
    }
    const n = data.added_count || 0;
    const names = data.added_names || [];
    const errs = data.errors || [];
    let msg = `Импорт выполнен. Добавлено: ${n}.`;
    if (names.length) msg += ' ' + names.join(', ');
    if (errs.length) msg += ` Ошибки: ${errs.length}.`;
    resultEl.textContent = msg;
    resultEl.classList.remove('db-import-result--error');
    resultEl.classList.add('db-import-result--ok');
    showToast('Импорт выполнен', 'success');
    loadDbEmployees();
  } catch (e) {
    resultEl.textContent = 'Ошибка: ' + e.message;
    resultEl.classList.add('db-import-result--error');
    showToast('Ошибка импорта', 'error');
  }
}

function initDbSection() {
  const viewBtns = document.querySelectorAll('.db-view-btn');
  viewBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      currentDbView = btn.dataset.view || 'all';
      viewBtns.forEach(b => b.classList.remove('db-view-btn--active'));
      btn.classList.add('db-view-btn--active');
      loadDbEmployees();
    });
  });
  const fileInput = document.getElementById('dbImportFile');
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (f) {
        doDbImport(f);
        e.target.value = '';
      }
    });
  }
}

function loadDb() {
  if (document.getElementById('section-db') && document.getElementById('dbTableHead')) {
    initDbSection();
    loadDbEmployees();
  }
}

if (typeof window !== 'undefined') {
  window.loadDb = loadDb;
}
