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
/** Last loaded settings snapshot for change detection (Task 7). */
let lastTelegram = {};
let lastLlm = {};

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

/** Show confirmation modal; resolve with true if user confirms, false if cancel. */
function confirmUnbindToken(serviceName) {
  return new Promise((resolve) => {
    const overlay = document.getElementById('confirmModalOverlay');
    const textEl = document.getElementById('confirmModalText');
    const cancelBtn = document.getElementById('confirmModalCancel');
    const confirmBtn = document.getElementById('confirmModalConfirm');
    textEl.textContent = `Текущий токен будет удалён. Сервис ${serviceName} перестанет работать до привязки нового токена.`;
    overlay.hidden = false;
    const cleanup = () => {
      overlay.hidden = true;
      cancelBtn.removeEventListener('click', onCancel);
      confirmBtn.removeEventListener('click', onConfirm);
    };
    const onCancel = () => {
      cleanup();
      resolve(false);
    };
    const onConfirm = () => {
      cleanup();
      resolve(true);
    };
    cancelBtn.addEventListener('click', onCancel);
    confirmBtn.addEventListener('click', onConfirm);
  });
}

/** True if we have token (typed or from placeholder/masked). Task 5: empty field + active token = valid. */
function hasTelegramTokenInput() {
  const tokenEl = document.getElementById('telegramToken');
  const v = (tokenEl?.value || '').trim();
  return !!v;
}

function isTelegramFormValid() {
  if (hasTelegramTokenInput()) return true;
  if (lastTelegram.isActive && lastTelegram.activeTokenMasked) return true;
  const tokenEl = document.getElementById('telegramToken');
  const placeholder = (tokenEl?.placeholder || '').trim();
  const defaultPh = 'Токен бота';
  return !!(placeholder && placeholder !== defaultPh);
}

/** Task 5: empty apiKey + active token = valid (we keep existing key). */
function isLlmFormValid() {
  const llmType = (document.getElementById('llmType')?.value || '').trim();
  const modelType = (document.getElementById('llmModel')?.value || '').trim();
  const apiKeyEl = document.getElementById('llmApiKey');
  const apiKey = (apiKeyEl?.value || '').trim();
  if (!llmType || !modelType) return false;
  if (llmType.toLowerCase() === 'ollama') return true;
  if (apiKey) return true;
  if (lastLlm.isActive && lastLlm.activeTokenMasked) return true;
  const placeholder = (apiKeyEl?.placeholder || '').trim();
  const defaultPh = 'Ключ API';
  return !!(placeholder && placeholder !== defaultPh);
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
    lastTelegram = { ...tg };

    document.getElementById('telegramToken').value = '';
    document.getElementById('telegramToken').placeholder = tg.accessTokenMasked || 'Токен бота';
    document.getElementById('telegramBaseUrl').value = tg.baseUrl || TELEGRAM_DEFAULT_BASE_URL;

    const telegramActiveEl = document.getElementById('telegramActiveToken');
    const telegramActiveValueEl = document.getElementById('telegramActiveTokenValue');
    if (tg.isActive && tg.activeTokenMasked) {
      telegramActiveEl.hidden = false;
      telegramActiveValueEl.textContent = tg.activeTokenMasked;
    } else {
      telegramActiveEl.hidden = true;
      telegramActiveValueEl.textContent = '';
    }

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
    lastLlm = { ...llm };
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
    const llmActiveEl = document.getElementById('llmActiveToken');
    const llmActiveValueEl = document.getElementById('llmActiveTokenValue');
    if (llm.isActive && llm.activeTokenMasked) {
      llmActiveEl.hidden = false;
      llmActiveValueEl.textContent = llm.activeTokenMasked;
    } else {
      llmActiveEl.hidden = true;
      llmActiveValueEl.textContent = '';
    }
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
    const placeholder = (tokenEl?.placeholder || '').trim();
    if ((placeholder && placeholder !== defaultPlaceholder) || (tokenEl?.value || '').trim()) {
      telegramTest();
    }
  }, STATUS_CHECK_INTERVAL_MS);
}

function stopTelegramAutoCheck() {
  if (telegramCheckTimer) {
    clearInterval(telegramCheckTimer);
    telegramCheckTimer = null;
  }
}

function stopLlmAutoCheck() {
  if (llmCheckTimer) {
    clearInterval(llmCheckTimer);
    llmCheckTimer = null;
  }
}

async function telegramSave() {
  const tokenEl = document.getElementById('telegramToken');
  const token = (tokenEl?.value || '').trim();
  let baseUrl = (document.getElementById('telegramBaseUrl')?.value || '').trim();
  if (!baseUrl) baseUrl = TELEGRAM_DEFAULT_BASE_URL;

  setFieldError('telegramToken', 'telegramFieldError', '');
  if (!token && !(lastTelegram.isActive && lastTelegram.activeTokenMasked)) {
    showToast('Заполните обязательные поля', 'warning');
    setFieldError('telegramToken', 'telegramFieldError', 'Заполните обязательные поля');
    return;
  }

  const btn = document.getElementById('telegramSave');
  setButtonLoading(btn, true);
  try {
    const r = await api('/api/settings/telegram', {
      method: 'PUT',
      body: JSON.stringify({ accessToken: token || null, baseUrl }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || r.statusText);
    }
    const data = await r.json();
    const applied = data.applied === true;
    const tg = data.telegram || {};
    if (applied) {
      showToast('Настройки сохранены и применены', 'success');
    } else {
      showToast('Ошибка подключения. Сервис остановлен. Проверьте токен', 'error');
    }
    setTelegramStatus(
      tg.connectionStatus === 'success' ? 'success' : tg.connectionStatus === 'not_configured' ? 'not_configured' : 'failed',
      tg.connectionStatus === 'success'
        ? 'Connection tested successfully'
        : tg.connectionStatus === 'not_configured'
          ? 'Not configured'
          : 'Connection failed'
    );
    document.getElementById('telegramToken').value = '';
    document.getElementById('telegramToken').placeholder = tg.accessTokenMasked || 'Токен бота';
    const telegramActiveEl = document.getElementById('telegramActiveToken');
    const telegramActiveValueEl = document.getElementById('telegramActiveTokenValue');
    if (tg.isActive && tg.activeTokenMasked) {
      telegramActiveEl.hidden = false;
      telegramActiveValueEl.textContent = tg.activeTokenMasked;
    } else {
      telegramActiveEl.hidden = true;
      telegramActiveValueEl.textContent = '';
    }
    if (!telegramCheckTimer) startTelegramAutoCheck();
  } catch (e) {
    showToast('Ошибка сохранения: ' + e.message, 'error');
  } finally {
    setButtonLoading(btn, false);
    updateTelegramSaveDisabled();
  }
}

async function telegramClear() {
  const btn = document.getElementById('telegramClear');
  if (!btn) return;
  setButtonLoading(btn, true);
  try {
    const r = await api('/api/settings/telegram', { method: 'DELETE' });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || r.statusText);
    }
    stopTelegramAutoCheck();
    await loadSettings();
    showToast('Ключи Telegram удалены', 'success');
  } catch (e) {
    showToast('Ошибка: ' + e.message, 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

async function telegramTokenDelete() {
  const ok = await confirmUnbindToken('Телеграм бот');
  if (!ok) return;
  const btn = document.getElementById('telegramTokenDelete');
  if (btn) setButtonLoading(btn, true);
  try {
    const r = await api('/api/settings/telegram/token', { method: 'DELETE' });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || r.statusText);
    }
    stopTelegramAutoCheck();
    await loadSettings();
    showToast('Токен удалён. Сервис остановлен', 'success');
  } catch (e) {
    showToast('Ошибка: ' + e.message, 'error');
  } finally {
    if (btn) setButtonLoading(btn, false);
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

/** Detect which LLM fields changed (Task 7). Credential-related require connection check. */
function getLlmChangedFields() {
  const llmType = (document.getElementById('llmType')?.value || '').trim();
  const apiKey = (document.getElementById('llmApiKey')?.value || '').trim();
  let baseUrl = (document.getElementById('llmBaseUrl')?.value || '').trim();
  const modelType = (document.getElementById('llmModel')?.value || '').trim();
  const systemPrompt = (document.getElementById('llmSystemPrompt')?.value || '').trim() || null;
  const prov = getProviderById(llmType);
  if (!baseUrl && prov?.defaultBaseUrl) baseUrl = prov.defaultBaseUrl;
  const prev = lastLlm || {};
  const changed = [];
  if (llmType !== (prev.llmType || '')) changed.push('llmType');
  if (apiKey) changed.push('apiKey');
  if (baseUrl !== (prev.baseUrl || '')) changed.push('baseUrl');
  if (modelType !== (prev.modelType || '')) changed.push('modelType');
  if ((systemPrompt || '') !== (prev.systemPrompt || '')) changed.push('systemPrompt');
  return { changed, llmType, apiKey, baseUrl, modelType, systemPrompt };
}

async function llmSave() {
  const { changed, llmType, apiKey, baseUrl, modelType, systemPrompt } = getLlmChangedFields();

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
  if (!apiKey && llmType.toLowerCase() !== 'ollama' && !(lastLlm.isActive && lastLlm.activeTokenMasked)) {
    showToast('Введите API key', 'warning');
    setFieldError('llmApiKey', 'llmFieldError', 'Введите API key');
    document.getElementById('llmApiKey')?.classList.add('field-input--error');
    return;
  }

  const requiresConnectionCheck = changed.some((f) => ['llmType', 'apiKey', 'baseUrl'].includes(f));
  const onlyModelOrPrompt = changed.length > 0 && !requiresConnectionCheck && (changed.includes('modelType') || changed.includes('systemPrompt'));

  if (changed.length === 0) {
    showToast('Нет изменений', 'success');
    return;
  }

  const btn = document.getElementById('llmSave');
  setButtonLoading(btn, true);
  try {
    if (onlyModelOrPrompt) {
      const r = await api('/api/settings/llm', {
        method: 'PATCH',
        body: JSON.stringify({ modelType, systemPrompt }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || r.statusText);
      }
      const data = await r.json();
      lastLlm = { ...data.llm };
      showToast(modelType !== (lastLlm.modelType || '') ? `Модель изменена на ${modelType}` : 'Системный промпт обновлён', 'success');
      setLlmStatus(
        data.llm?.connectionStatus === 'success' ? 'success' : data.llm?.connectionStatus === 'not_configured' ? 'not_configured' : 'failed',
        data.llm?.connectionStatus === 'success'
          ? 'Connection tested successfully'
          : data.llm?.connectionStatus === 'not_configured'
            ? 'Not configured'
            : 'Connection failed'
      );
      const llmActiveEl = document.getElementById('llmActiveToken');
      const llmActiveValueEl = document.getElementById('llmActiveTokenValue');
      if (data.llm?.isActive && data.llm?.activeTokenMasked) {
        llmActiveEl.hidden = false;
        llmActiveValueEl.textContent = data.llm.activeTokenMasked;
      } else {
        llmActiveEl.hidden = true;
        llmActiveValueEl.textContent = '';
      }
    } else {
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
      lastLlm = { ...data.llm };
      if (applied) {
        showToast('Настройки сохранены и применены', 'success');
      } else {
        showToast('Ошибка подключения. Сервис остановлен. Проверьте токен', 'error');
      }
      setLlmStatus(
        data.llm?.connectionStatus === 'success' ? 'success' : data.llm?.connectionStatus === 'not_configured' ? 'not_configured' : 'failed',
        data.llm?.connectionStatus === 'success'
          ? 'Connection tested successfully'
          : data.llm?.connectionStatus === 'not_configured'
            ? 'Not configured'
            : 'Connection failed'
      );
      document.getElementById('llmApiKey').value = '';
      document.getElementById('llmApiKey').placeholder = data.llm?.apiKeyMasked || 'Ключ API';
      const llmActiveEl = document.getElementById('llmActiveToken');
      const llmActiveValueEl = document.getElementById('llmActiveTokenValue');
      if (data.llm?.isActive && data.llm?.activeTokenMasked) {
        llmActiveEl.hidden = false;
        llmActiveValueEl.textContent = data.llm.activeTokenMasked;
      } else {
        llmActiveEl.hidden = true;
        llmActiveValueEl.textContent = '';
      }
      if (!llmCheckTimer) startLlmAutoCheck();
    }
  } catch (e) {
    showToast('Ошибка сохранения: ' + e.message, 'error');
  } finally {
    setButtonLoading(btn, false);
    updateLlmSaveDisabled();
  }
}

async function llmClear() {
  const btn = document.getElementById('llmClear');
  if (!btn) return;
  setButtonLoading(btn, true);
  try {
    const r = await api('/api/settings/llm', { method: 'DELETE' });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || r.statusText);
    }
    stopLlmAutoCheck();
    await loadSettings();
    showToast('Ключи LLM удалены', 'success');
  } catch (e) {
    showToast('Ошибка: ' + e.message, 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

async function llmTokenDelete() {
  const ok = await confirmUnbindToken('LLM');
  if (!ok) return;
  const btn = document.getElementById('llmTokenDelete');
  if (btn) setButtonLoading(btn, true);
  try {
    const r = await api('/api/settings/llm/token', { method: 'DELETE' });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || r.statusText);
    }
    stopLlmAutoCheck();
    await loadSettings();
    showToast('Токен удалён. Сервис остановлен', 'success');
  } catch (e) {
    showToast('Ошибка: ' + e.message, 'error');
  } finally {
    if (btn) setButtonLoading(btn, false);
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
  document.getElementById('telegramClear').addEventListener('click', telegramClear);
  document.getElementById('telegramTokenDelete')?.addEventListener('click', telegramTokenDelete);

  document.getElementById('llmType')?.addEventListener('change', onLlmTypeChange);
  document.getElementById('llmRetry')?.addEventListener('click', () => llmTest());
  document.getElementById('llmSave')?.addEventListener('click', llmSave);
  document.getElementById('llmClear')?.addEventListener('click', llmClear);
  document.getElementById('llmTokenDelete')?.addEventListener('click', llmTokenDelete);

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
