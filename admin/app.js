/**
 * Admin panel: load settings, Telegram block (Retry, Save), toasts, auto-check.
 * Phase 3: LLM block — providers, settings, retry, save.
 * PRD 5.4: tokens/API keys only as masked (placeholder); never log full values on client.
 */

const TELEGRAM_DEFAULT_BASE_URL = 'https://api.telegram.org';
const STATUS_CHECK_INTERVAL_MS = 10000;

let telegramCheckTimer = null;
let llmCheckTimer = null;
/** @type {Array<{id: string, name: string, defaultBaseUrl: string, models: {standard: string[], reasoning: string[]}}>} */
let llmProviders = [];

function getHeaders() {
  const key = document.getElementById('adminKey').value.trim();
  const headers = { 'Content-Type': 'application/json' };
  if (key) headers['X-Admin-Key'] = key;
  return headers;
}

function api(path, options = {}) {
  return fetch(path, {
    ...options,
    headers: { ...getHeaders(), ...options.headers },
  });
}

/** PRD 5.6: success / warning (saved but not applied, validation) / error */
function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function setButtonLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  btn.classList.toggle('btn--loading', loading);
}

function setFieldError(fieldId, errorElId, message) {
  const field = document.getElementById(fieldId);
  const errorEl = document.getElementById(errorElId);
  if (field) field.classList.toggle('field-input--error', !!message);
  if (errorEl) {
    errorEl.textContent = message || '';
  }
}

function isTelegramFormValid() {
  const tokenEl = document.getElementById('telegramToken');
  const v = (tokenEl?.value || '').trim();
  const placeholder = (tokenEl?.placeholder || '').trim();
  const defaultPh = 'Токен бота';
  return !!(v || (placeholder && placeholder !== defaultPh));
}

function isLlmFormValid() {
  const llmType = (document.getElementById('llmType')?.value || '').trim();
  const modelType = (document.getElementById('llmModel')?.value || '').trim();
  const apiKeyEl = document.getElementById('llmApiKey');
  const apiKey = (apiKeyEl?.value || '').trim();
  const placeholder = (apiKeyEl?.placeholder || '').trim();
  const defaultPh = 'Ключ API';
  const hasKey = !!(apiKey || (placeholder && placeholder !== defaultPh));
  if (!llmType || !modelType) return false;
  if (llmType.toLowerCase() === 'ollama') return true;
  return hasKey;
}

function updateTelegramSaveDisabled() {
  const btn = document.getElementById('telegramSave');
  if (btn) btn.disabled = !isTelegramFormValid();
}

function updateLlmSaveDisabled() {
  const btn = document.getElementById('llmSave');
  if (btn) btn.disabled = !isLlmFormValid();
}

function setTelegramStatus(status, text) {
  const bar = document.getElementById('telegramStatusBar');
  const textEl = document.getElementById('telegramStatusText');
  bar.dataset.status = status;
  textEl.textContent = text;
}

function setTelegramChecking() {
  setTelegramStatus('checking', 'Checking connection...');
}

function setLlmStatus(status, text) {
  const bar = document.getElementById('llmStatusBar');
  const textEl = document.getElementById('llmStatusText');
  if (!bar || !textEl) return;
  bar.dataset.status = status;
  textEl.textContent = text;
}

function setLlmChecking() {
  setLlmStatus('checking', 'Checking connection...');
}

async function loadLlmProviders() {
  const r = await api('/api/settings/llm/providers');
  if (!r.ok) return [];
  const d = await r.json();
  llmProviders = d.providers || [];
  return llmProviders;
}

function getProviderById(id) {
  return llmProviders.find((p) => p.id === id) || null;
}

function fillLlmTypeSelect(selectedId) {
  const sel = document.getElementById('llmType');
  if (!sel) return;
  sel.innerHTML =
    '<option value="">— выберите провайдера —</option>' +
    llmProviders.map((p) => `<option value="${p.id}">${p.name}</option>`).join('');
  if (selectedId) sel.value = selectedId;
}

function fillLlmModelSelect(providerId, selectedModel) {
  const sel = document.getElementById('llmModel');
  if (!sel) return;
  sel.innerHTML = '<option value="">— выберите модель —</option>';
  const prov = getProviderById(providerId);
  if (!prov || !prov.models) return;
  const std = prov.models.standard || [];
  const reas = prov.models.reasoning || [];
  if (std.length) {
    const g = document.createElement('optgroup');
    g.label = 'Стандартные модели';
    std.forEach((m) => {
      const o = document.createElement('option');
      o.value = m;
      o.textContent = m;
      g.appendChild(o);
    });
    sel.appendChild(g);
  }
  if (reas.length) {
    const g = document.createElement('optgroup');
    g.label = 'Reasoning модели (🧠)';
    reas.forEach((m) => {
      const o = document.createElement('option');
      o.value = m;
      o.textContent = m;
      g.appendChild(o);
    });
    sel.appendChild(g);
  }
  if (selectedModel && (std.includes(selectedModel) || reas.includes(selectedModel))) {
    sel.value = selectedModel;
  } else if (std.length) {
    sel.value = std[0];
  } else if (reas.length) {
    sel.value = reas[0];
  }
}

function updateLlmBaseUrlHint(providerId) {
  const hint = document.getElementById('llmBaseUrlHint');
  if (!hint) return;
  const prov = getProviderById(providerId);
  hint.textContent = prov?.defaultBaseUrl ? `По умолчанию: ${prov.defaultBaseUrl}` : '';
}

async function loadSettings() {
  try {
    const r = await api('/api/settings');
    if (!r.ok) {
      if (r.status === 403) {
        showToast('Требуется Admin key (заголовок X-Admin-Key)', 'warning');
        return;
      }
      throw new Error(r.statusText);
    }
    const data = await r.json();
    const tg = data.telegram || {};

    document.getElementById('telegramToken').value = '';
    document.getElementById('telegramToken').placeholder = tg.accessTokenMasked || 'Токен бота';
    document.getElementById('telegramBaseUrl').value = tg.baseUrl || TELEGRAM_DEFAULT_BASE_URL;

    const status = tg.connectionStatus || 'not_configured';
    const statusText =
      status === 'success'
        ? 'Connection tested successfully'
        : status === 'failed'
          ? 'Connection failed'
          : status === 'checking'
            ? 'Checking connection...'
            : 'Not configured';
    setTelegramStatus(status, statusText);

    if (tg.accessTokenMasked && telegramCheckTimer === null) {
      startTelegramAutoCheck();
    }
    updateTelegramSaveDisabled();

    const llm = data.llm || {};
    if (llmProviders.length === 0) {
      await loadLlmProviders();
    }
    fillLlmTypeSelect(llm.llmType || '');
    fillLlmModelSelect(llm.llmType || '', llm.modelType || '');
    const baseUrlEl = document.getElementById('llmBaseUrl');
    const apiKeyEl = document.getElementById('llmApiKey');
    const systemPromptEl = document.getElementById('llmSystemPrompt');
    if (baseUrlEl) baseUrlEl.value = llm.baseUrl || '';
    if (apiKeyEl) {
      apiKeyEl.value = '';
      apiKeyEl.placeholder = llm.apiKeyMasked || 'Ключ API';
    }
    if (systemPromptEl) systemPromptEl.value = llm.systemPrompt || '';
    updateLlmBaseUrlHint(llm.llmType || '');
    const llmStatus = llm.connectionStatus || 'not_configured';
    const llmStatusText =
      llmStatus === 'success'
        ? 'Connection tested successfully'
        : llmStatus === 'failed'
          ? 'Connection failed'
          : llmStatus === 'checking'
            ? 'Checking connection...'
            : 'Not configured';
    setLlmStatus(llmStatus, llmStatusText);
    if (llm.apiKeyMasked && llmCheckTimer === null) {
      startLlmAutoCheck();
    }
  } catch (e) {
    showToast('Ошибка загрузки настроек: ' + e.message, 'error');
  }
}

async function telegramTest() {
  setTelegramChecking();
  const retryBtn = document.getElementById('telegramRetry');
  setButtonLoading(retryBtn, true);
  try {
    const r = await api('/api/settings/telegram/test', { method: 'POST' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      setTelegramStatus('failed', data.detail || r.statusText || 'Connection failed');
      showToast(data.detail || r.statusText || 'Ошибка проверки', 'error');
      return;
    }
    const status = data.status || 'failed';
    const text =
      status === 'success'
        ? 'Connection tested successfully'
        : status === 'not_configured'
          ? 'Not configured'
          : data.message || 'Connection failed';
    setTelegramStatus(status === 'success' ? 'success' : status === 'not_configured' ? 'not_configured' : 'failed', text);
  } catch (e) {
    setTelegramStatus('failed', 'Connection failed');
    showToast(e.message, 'error');
  } finally {
    setButtonLoading(document.getElementById('telegramRetry'), false);
  }
}

function startTelegramAutoCheck() {
  if (telegramCheckTimer) return;
  const defaultPlaceholder = 'Токен бота';
  telegramCheckTimer = setInterval(() => {
    const tokenEl = document.getElementById('telegramToken');
    const placeholder = (tokenEl.placeholder || '').trim();
    if ((placeholder && placeholder !== defaultPlaceholder) || tokenEl.value.trim()) {
      telegramTest();
    }
  }, STATUS_CHECK_INTERVAL_MS);
}

async function telegramSave() {
  const tokenEl = document.getElementById('telegramToken');
  const token = (tokenEl?.value || '').trim();
  let baseUrl = (document.getElementById('telegramBaseUrl')?.value || '').trim();
  if (!baseUrl) baseUrl = TELEGRAM_DEFAULT_BASE_URL;

  setFieldError('telegramToken', 'telegramFieldError', '');
  if (!token) {
    showToast('Заполните обязательные поля', 'warning');
    setFieldError('telegramToken', 'telegramFieldError', 'Заполните обязательные поля');
    return;
  }

  const btn = document.getElementById('telegramSave');
  setButtonLoading(btn, true);
  try {
    const r = await api('/api/settings/telegram', {
      method: 'PUT',
      body: JSON.stringify({ accessToken: token, baseUrl }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || r.statusText);
    }
    const data = await r.json();
    const applied = data.applied === true;
    if (applied) {
      showToast('Настройки сохранены и применены', 'success');
    } else {
      showToast('Настройки сохранены, но не применены (ошибка подключения)', 'warning');
    }
    setTelegramStatus(
      data.telegram?.connectionStatus === 'success' ? 'success' : 'failed',
      data.telegram?.connectionStatus === 'success'
        ? 'Connection tested successfully'
        : data.telegram?.connectionStatus === 'not_configured'
          ? 'Not configured'
          : 'Connection failed'
    );
    document.getElementById('telegramToken').value = '';
    document.getElementById('telegramToken').placeholder = data.telegram?.accessTokenMasked || 'Токен бота';
    if (!telegramCheckTimer) startTelegramAutoCheck();
  } catch (e) {
    showToast('Ошибка сохранения: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function llmTest() {
  setLlmChecking();
  const retryBtn = document.getElementById('llmRetry');
  setButtonLoading(retryBtn, true);
  try {
    const r = await api('/api/settings/llm/test', { method: 'POST' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      setLlmStatus('failed', data.detail || r.statusText || 'Connection failed');
      showToast(data.detail || r.statusText || 'Ошибка проверки', 'error');
      return;
    }
    const status = data.status || 'failed';
    const text =
      status === 'success'
        ? 'Connection tested successfully'
        : status === 'not_configured'
          ? 'Not configured'
          : data.message || 'Connection failed';
    setLlmStatus(
      status === 'success' ? 'success' : status === 'not_configured' ? 'not_configured' : 'failed',
      text
    );
  } catch (e) {
    setLlmStatus('failed', 'Connection failed');
    showToast(e.message, 'error');
  } finally {
    setButtonLoading(retryBtn, false);
  }
}

function startLlmAutoCheck() {
  if (llmCheckTimer) return;
  const defaultPlaceholder = 'Ключ API';
  llmCheckTimer = setInterval(() => {
    const apiKeyEl = document.getElementById('llmApiKey');
    const placeholder = (apiKeyEl?.placeholder || '').trim();
    if ((placeholder && placeholder !== defaultPlaceholder) || (apiKeyEl?.value || '').trim()) {
      llmTest();
    }
  }, STATUS_CHECK_INTERVAL_MS);
}

async function llmSave() {
  const llmType = (document.getElementById('llmType')?.value || '').trim();
  const apiKey = (document.getElementById('llmApiKey')?.value || '').trim();
  let baseUrl = (document.getElementById('llmBaseUrl')?.value || '').trim();
  const modelType = (document.getElementById('llmModel')?.value || '').trim();
  const systemPrompt = (document.getElementById('llmSystemPrompt')?.value || '').trim() || null;

  setFieldError('llmType', 'llmFieldError', '');
  document.getElementById('llmType')?.classList.remove('field-input--error');
  document.getElementById('llmModel')?.classList.remove('field-input--error');
  document.getElementById('llmApiKey')?.classList.remove('field-input--error');

  if (!llmType || !modelType) {
    showToast('Заполните обязательные поля', 'warning');
    setFieldError(llmType ? 'llmModel' : 'llmType', 'llmFieldError', 'Заполните обязательные поля');
    if (!llmType) document.getElementById('llmType')?.classList.add('field-input--error');
    if (!modelType) document.getElementById('llmModel')?.classList.add('field-input--error');
    return;
  }
  if (!apiKey && llmType.toLowerCase() !== 'ollama') {
    showToast('Заполните обязательные поля', 'warning');
    setFieldError('llmApiKey', 'llmFieldError', 'Заполните обязательные поля');
    document.getElementById('llmApiKey')?.classList.add('field-input--error');
    return;
  }

  if (!baseUrl) {
    const prov = getProviderById(llmType);
    baseUrl = prov?.defaultBaseUrl || '';
  }

  const btn = document.getElementById('llmSave');
  if (btn) btn.disabled = true;
  try {
    const r = await api('/api/settings/llm', {
      method: 'PUT',
      body: JSON.stringify({
        llmType,
        apiKey: apiKey || null,
        baseUrl,
        modelType,
        systemPrompt,
      }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || r.statusText);
    }
    const data = await r.json();
    const applied = data.applied === true;
    if (applied) {
      showToast('Настройки сохранены и применены', 'success');
    } else {
      showToast('Настройки сохранены, но не применены (ошибка подключения)', 'warning');
    }
    setLlmStatus(
      data.llm?.connectionStatus === 'success' ? 'success' : 'failed',
      data.llm?.connectionStatus === 'success'
        ? 'Connection tested successfully'
        : data.llm?.connectionStatus === 'not_configured'
          ? 'Not configured'
          : 'Connection failed'
    );
    document.getElementById('llmApiKey').value = '';
    document.getElementById('llmApiKey').placeholder = data.llm?.apiKeyMasked || 'Ключ API';
    if (!llmCheckTimer) startLlmAutoCheck();
  } catch (e) {
    showToast('Ошибка сохранения: ' + e.message, 'error');
  } finally {
    setButtonLoading(btn, false);
    updateLlmSaveDisabled();
  }
}

function onLlmTypeChange() {
  const providerId = document.getElementById('llmType')?.value || '';
  const prov = getProviderById(providerId);
  const baseUrlEl = document.getElementById('llmBaseUrl');
  if (baseUrlEl && prov?.defaultBaseUrl) baseUrlEl.value = prov.defaultBaseUrl;
  updateLlmBaseUrlHint(providerId);
  fillLlmModelSelect(providerId, null);
}

document.addEventListener('DOMContentLoaded', () => {
  const savedKey = sessionStorage.getItem('adminApiKey');
  if (savedKey) document.getElementById('adminKey').value = savedKey;
  document.getElementById('adminKey').addEventListener('change', (e) => {
    sessionStorage.setItem('adminApiKey', e.target.value);
  });

  loadSettings();

  document.getElementById('telegramRetry').addEventListener('click', () => {
    telegramTest();
  });
  document.getElementById('telegramSave').addEventListener('click', telegramSave);

  document.getElementById('llmType')?.addEventListener('change', onLlmTypeChange);
  document.getElementById('llmRetry')?.addEventListener('click', () => llmTest());
  document.getElementById('llmSave')?.addEventListener('click', llmSave);

  document.getElementById('telegramToken')?.addEventListener('input', () => {
    setFieldError('telegramToken', 'telegramFieldError', '');
    updateTelegramSaveDisabled();
  });
  ['llmType', 'llmModel', 'llmApiKey'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        setFieldError('llmType', 'llmFieldError', '');
        setFieldError('llmModel', 'llmFieldError', '');
        setFieldError('llmApiKey', 'llmFieldError', '');
        document.getElementById('llmType')?.classList.remove('field-input--error');
        document.getElementById('llmModel')?.classList.remove('field-input--error');
        document.getElementById('llmApiKey')?.classList.remove('field-input--error');
        updateLlmSaveDisabled();
      });
    }
  });
  document.getElementById('llmApiKey')?.addEventListener('input', () => {
    setFieldError('llmApiKey', 'llmFieldError', '');
    document.getElementById('llmApiKey')?.classList.remove('field-input--error');
    updateLlmSaveDisabled();
  });
});
