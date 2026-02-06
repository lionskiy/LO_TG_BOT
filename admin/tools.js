/**
 * Admin Tools section: list tools, enable/disable, reload plugins.
 * Uses same auth as app.js (X-Admin-Key from #adminKey).
 */
(function () {
  function getHeaders() {
    const key = document.getElementById('adminKey')?.value?.trim();
    const headers = { 'Content-Type': 'application/json' };
    if (key) headers['X-Admin-Key'] = key;
    return headers;
  }

  function api(path, options = {}) {
    return fetch(path, { ...options, headers: { ...getHeaders(), ...options.headers } });
  }

  function showToast(message, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const el = document.createElement('div');
    el.className = 'toast toast--' + (type || 'success');
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  function setButtonLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle('btn--loading', loading);
  }

  /** Group tools by plugin_id */
  function groupByPlugin(tools) {
    const byPlugin = {};
    tools.forEach((t) => {
      if (!byPlugin[t.plugin_id]) {
        byPlugin[t.plugin_id] = { pluginName: t.plugin_name || t.plugin_id, tools: [] };
      }
      byPlugin[t.plugin_id].tools.push(t);
    });
    return byPlugin;
  }

  function renderTools(data) {
    const listEl = document.getElementById('toolsList');
    const placeholderEl = document.getElementById('toolsPlaceholder');
    const summaryEl = document.getElementById('toolsSummary');
    if (!listEl) return;

    if (!data || !data.tools || data.tools.length === 0) {
      listEl.innerHTML = '';
      if (placeholderEl) placeholderEl.hidden = false;
      if (summaryEl) summaryEl.textContent = 'Всего: 0 | Включено: 0';
      return;
    }
    if (placeholderEl) placeholderEl.hidden = true;
    if (summaryEl) summaryEl.textContent = 'Всего: ' + data.total + ' | Включено: ' + (data.enabled_count || 0);

    const groups = groupByPlugin(data.tools);
    let html = '';
    Object.keys(groups).forEach((pluginId) => {
      const g = groups[pluginId];
      html += '<div class="tools-group"><h3 class="tools-group-title">' + escapeHtml(g.pluginName) + '</h3>';
      g.tools.forEach((t) => {
        const status = t.needs_config ? 'needs_config' : t.enabled ? 'enabled' : 'disabled';
        const statusLabel = t.needs_config ? 'Нужна настройка' : t.enabled ? 'Включён' : 'Выключен';
        html += '<div class="tools-card" data-tool="' + escapeHtml(t.name) + '">';
        html += '<div class="tools-card-header">';
        html += '<span class="tools-card-name">' + escapeHtml(t.name) + '</span>';
        html += '<span class="tools-card-status tools-card-status--' + status + '">' + statusLabel + '</span>';
        html += '</div>';
        html += '<p class="tools-card-desc">' + escapeHtml(t.description || '') + '</p>';
        html += '<div class="tools-card-actions">';
        if (t.enabled) {
          html += '<button type="button" class="btn btn-secondary btn-sm tools-btn-disable">Выключить</button>';
        } else {
          html += '<button type="button" class="btn btn-primary btn-sm tools-btn-enable">Включить</button>';
        }
        html += '</div></div>';
      });
      html += '</div>';
    });
    listEl.innerHTML = html;

    listEl.querySelectorAll('.tools-btn-enable').forEach((btn) => {
      btn.addEventListener('click', () => {
        const card = btn.closest('.tools-card');
        const name = card?.getAttribute('data-tool');
        if (name) enableTool(name);
      });
    });
    listEl.querySelectorAll('.tools-btn-disable').forEach((btn) => {
      btn.addEventListener('click', () => {
        const card = btn.closest('.tools-card');
        const name = card?.getAttribute('data-tool');
        if (name) disableTool(name);
      });
    });
  }

  function escapeHtml(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  async function loadTools() {
    const listEl = document.getElementById('toolsList');
    const summaryEl = document.getElementById('toolsSummary');
    if (summaryEl) summaryEl.textContent = 'Загрузка...';
    try {
      const r = await api('/api/tools');
      if (!r.ok) {
        if (r.status === 403) showToast('Требуется ключ администратора', 'error');
        else showToast('Ошибка загрузки: ' + r.status, 'error');
        if (summaryEl) summaryEl.textContent = 'Ошибка загрузки';
        return;
      }
      const data = await r.json();
      renderTools(data);
    } catch (e) {
      showToast('Ошибка сети', 'error');
      if (summaryEl) summaryEl.textContent = 'Ошибка';
    }
  }

  async function enableTool(name) {
    try {
      const r = await api('/api/tools/' + encodeURIComponent(name) + '/enable', { method: 'POST' });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        const msg = (data.detail && data.detail.message) || data.message || 'Не удалось включить';
        showToast(msg, 'error');
        return;
      }
      showToast('Инструмент включён');
      loadTools();
    } catch (e) {
      showToast('Ошибка', 'error');
    }
  }

  async function disableTool(name) {
    try {
      const r = await api('/api/tools/' + encodeURIComponent(name) + '/disable', { method: 'POST' });
      if (!r.ok) {
        showToast('Не удалось выключить', 'error');
        return;
      }
      showToast('Инструмент выключен');
      loadTools();
    } catch (e) {
      showToast('Ошибка', 'error');
    }
  }

  async function reloadPlugins() {
    const btn = document.getElementById('toolsReload');
    setButtonLoading(btn, true);
    try {
      const r = await api('/api/plugins/reload', { method: 'POST' });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        showToast(data.message || 'Ошибка перезагрузки', 'error');
        return;
      }
      showToast('Плагины перезагружены');
      loadTools();
    } catch (e) {
      showToast('Ошибка сети', 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    window.loadTools = loadTools;
    const reloadBtn = document.getElementById('toolsReload');
    if (reloadBtn) reloadBtn.addEventListener('click', reloadPlugins);
  });
})();
