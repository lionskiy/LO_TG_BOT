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
        if (t.has_settings) {
          html += '<button type="button" class="btn btn-secondary btn-sm tools-btn-settings">Настройки</button>';
        }
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
    listEl.querySelectorAll('.tools-btn-settings').forEach((btn) => {
      btn.addEventListener('click', () => {
        const card = btn.closest('.tools-card');
        const name = card?.getAttribute('data-tool');
        if (name) openToolSettingsModal(name);
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

  let currentToolSettingsName = null;

  function closeToolSettingsModal() {
    const overlay = document.getElementById('toolSettingsModalOverlay');
    if (overlay) overlay.setAttribute('hidden', '');
    currentToolSettingsName = null;
  }

  function buildSettingsForm(schema, currentSettings) {
    const form = document.getElementById('toolSettingsForm');
    if (!form) return;
    form.innerHTML = '';
    (schema || []).forEach((field) => {
      const key = field.key;
      const label = field.label || key;
      const type = (field.type || 'string').toLowerCase();
      const required = !!field.required;
      const desc = field.description || '';
      const value = currentSettings[key] != null ? String(currentSettings[key]) : (field.default != null ? String(field.default) : '');
      const wrap = document.createElement('label');
      wrap.className = 'field tool-settings-field';
      let input;
      if (type === 'boolean') {
        wrap.innerHTML =
          '<span class="field-label">' + escapeHtml(label) + '</span>';
        input = document.createElement('input');
        input.type = 'checkbox';
        input.name = key;
        input.className = 'field-input';
        input.checked = value === 'true' || value === '1';
        wrap.appendChild(input);
        if (desc) {
          const hint = document.createElement('span');
          hint.className = 'field-hint';
          hint.textContent = desc;
          wrap.appendChild(hint);
        }
      } else if (type === 'select') {
        wrap.innerHTML =
          '<span class="field-label">' + (required ? escapeHtml(label) + ' *' : escapeHtml(label)) + '</span>';
        input = document.createElement('select');
        input.name = key;
        input.className = 'field-input field-select';
        const options = field.options || [];
        options.forEach((opt) => {
          const o = document.createElement('option');
          o.value = typeof opt === 'object' ? (opt.value ?? opt) : opt;
          o.textContent = typeof opt === 'object' ? (opt.label ?? o.value) : opt;
          if (o.value === value) o.selected = true;
          input.appendChild(o);
        });
        wrap.appendChild(input);
        if (desc) {
          const hint = document.createElement('span');
          hint.className = 'field-hint';
          hint.textContent = desc;
          wrap.appendChild(hint);
        }
      } else {
        const isPassword = type === 'password';
        wrap.innerHTML =
          '<span class="field-label">' + (required ? escapeHtml(label) + ' *' : escapeHtml(label)) + '</span>';
        input = document.createElement('input');
        input.name = key;
        input.className = 'field-input';
        input.type = isPassword ? 'password' : type === 'number' ? 'number' : 'text';
        input.value = value;
        input.autocomplete = isPassword ? 'off' : '';
        wrap.appendChild(input);
        if (isPassword) {
          const toggle = document.createElement('button');
          toggle.type = 'button';
          toggle.className = 'field-password-toggle';
          toggle.setAttribute('aria-label', 'Показать пароль');
          toggle.textContent = '👁️';
          toggle.addEventListener('click', () => {
            const isPass = input.type === 'password';
            input.type = isPass ? 'text' : 'password';
            toggle.setAttribute('aria-label', isPass ? 'Скрыть пароль' : 'Показать пароль');
          });
          wrap.appendChild(toggle);
        }
        if (desc) {
          const hint = document.createElement('span');
          hint.className = 'field-hint';
          hint.textContent = desc;
          wrap.appendChild(hint);
        }
      }
      const errEl = document.createElement('span');
      errEl.className = 'field-error';
      errEl.setAttribute('data-field', key);
      wrap.appendChild(errEl);
      form.appendChild(wrap);
    });
  }

  function collectSettingsForm(schema) {
    const form = document.getElementById('toolSettingsForm');
    if (!form) return {};
    const out = {};
    (schema || []).forEach((field) => {
      const key = field.key;
      const type = (field.type || 'string').toLowerCase();
      const input = form.querySelector('[name="' + key + '"]');
      if (!input) return;
      if (type === 'boolean') {
        out[key] = input.checked;
      } else if (type === 'number') {
        const v = input.value.trim();
        out[key] = v === '' ? undefined : Number(v);
      } else {
        out[key] = input.value.trim() || undefined;
      }
    });
    return out;
  }

  function setToolSettingsFieldError(key, message) {
    const form = document.getElementById('toolSettingsForm');
    const errEl = form?.querySelector('.field-error[data-field="' + key + '"]');
    const wrap = form?.querySelector('.tool-settings-field [name="' + key + '"]')?.closest('.field');
    if (wrap) wrap.classList.toggle('field-input--error', !!message);
    if (errEl) errEl.textContent = message || '';
  }

  async function openToolSettingsModal(name) {
    const overlay = document.getElementById('toolSettingsModalOverlay');
    const titleEl = document.getElementById('toolSettingsModalTitle');
    const pluginInfoEl = document.getElementById('toolSettingsPluginInfo');
    const testBlock = document.getElementById('toolSettingsTestBlock');
    const testResult = document.getElementById('toolSettingsTestResult');
    if (!overlay || !titleEl) return;
    currentToolSettingsName = name;
    titleEl.textContent = 'Настройки: ' + name;
    if (pluginInfoEl) pluginInfoEl.textContent = '';
    if (testBlock) testBlock.setAttribute('hidden', '');
    if (testResult) testResult.setAttribute('hidden', '');
    buildSettingsForm([], {});
    overlay.removeAttribute('hidden');
    try {
      const r = await api('/api/tools/' + encodeURIComponent(name));
      if (!r.ok) {
        showToast('Не удалось загрузить настройки', 'error');
        closeToolSettingsModal();
        return;
      }
      const data = await r.json();
      if (pluginInfoEl) {
        pluginInfoEl.textContent = 'Плагин: ' + (data.plugin_name || data.plugin_id) + (data.plugin_version ? ' v' + data.plugin_version : '');
      }
      const schema = data.settings_schema || [];
      const hasPassword = schema.some((f) => (f.type || '').toLowerCase() === 'password');
      if (testBlock) {
        testBlock.hidden = !hasPassword;
      }
      buildSettingsForm(schema, data.current_settings || {});
    } catch (e) {
      showToast('Ошибка загрузки', 'error');
      closeToolSettingsModal();
    }
  }

  async function saveToolSettingsFromModal() {
    const name = currentToolSettingsName;
    if (!name) return;
    const r = await api('/api/tools/' + encodeURIComponent(name));
    if (!r.ok) return;
    const data = await r.json();
    const schema = data.settings_schema || [];
    const form = document.getElementById('toolSettingsForm');
    schema.forEach((f) => setToolSettingsFieldError(f.key, ''));
    const payload = collectSettingsForm(schema);
    const requiredMissing = schema.filter((f) => f.required && (payload[f.key] == null || String(payload[f.key]).trim() === ''));
    if (requiredMissing.length) {
      requiredMissing.forEach((f) => setToolSettingsFieldError(f.key, 'Обязательное поле'));
      showToast('Заполните обязательные поля', 'error');
      return;
    }
    const saveBtn = document.getElementById('toolSettingsModalSave');
    setButtonLoading(saveBtn, true);
    try {
      const putRes = await api('/api/tools/' + encodeURIComponent(name) + '/settings', {
        method: 'PUT',
        body: JSON.stringify({ settings: payload }),
      });
      const putData = await putRes.json().catch(() => ({}));
      if (!putRes.ok) {
        const errors = putData.detail?.errors || putData.errors || [];
        errors.forEach((err) => setToolSettingsFieldError(err.field || err.key, err.error || err.message));
        showToast(putData.detail?.message || 'Ошибка сохранения', 'error');
        return;
      }
      showToast('Настройки сохранены');
      closeToolSettingsModal();
      loadTools();
    } catch (e) {
      showToast('Ошибка сети', 'error');
    } finally {
      setButtonLoading(saveBtn, false);
    }
  }

  function wireToolSettingsModal() {
    const overlay = document.getElementById('toolSettingsModalOverlay');
    const modal = document.getElementById('toolSettingsModal');
    const closeBtn = document.getElementById('toolSettingsModalClose');
    const cancelBtn = document.getElementById('toolSettingsModalCancel');
    const saveBtn = document.getElementById('toolSettingsModalSave');
    const testBtn = document.getElementById('toolSettingsTestBtn');
    const testResult = document.getElementById('toolSettingsTestResult');
    const stopProp = (e) => e.stopPropagation();
    if (modal) modal.addEventListener('click', stopProp);
    overlay?.addEventListener('click', (e) => {
      if (e.target === overlay) closeToolSettingsModal();
    });
    closeBtn?.addEventListener('click', closeToolSettingsModal);
    cancelBtn?.addEventListener('click', closeToolSettingsModal);
    saveBtn?.addEventListener('click', () => saveToolSettingsFromModal());
    testBtn?.addEventListener('click', async () => {
      const name = currentToolSettingsName;
      if (!name) return;
      setButtonLoading(testBtn, true);
      if (testResult) testResult.hidden = false;
      try {
        const r = await api('/api/tools/' + encodeURIComponent(name) + '/test', { method: 'POST' });
        const data = await r.json().catch(() => ({}));
        if (testResult) {
          testResult.textContent = r.ok && data.success ? 'Подключение успешно' : (data.message || 'Ошибка проверки');
          testResult.className = 'tool-settings-test-result ' + (r.ok && data.success ? 'tool-settings-test-result--success' : 'tool-settings-test-result--error');
        }
      } catch (e) {
        if (testResult) {
          testResult.textContent = 'Ошибка сети';
          testResult.className = 'tool-settings-test-result tool-settings-test-result--error';
        }
      } finally {
        setButtonLoading(testBtn, false);
      }
    });
  }

  // Expose loadTools before DOMContentLoaded so app.js can call it when opening #tools on initial load/refresh
  window.loadTools = loadTools;

  document.addEventListener('DOMContentLoaded', () => {
    wireToolSettingsModal();
    const reloadBtn = document.getElementById('toolsReload');
    if (reloadBtn) reloadBtn.addEventListener('click', reloadPlugins);
  });
})();
