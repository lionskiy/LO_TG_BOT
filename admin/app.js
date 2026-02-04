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
    const modal = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmModalTitle');
    const textEl = document.getElementById('confirmModalText');
    const cancelBtn = document.getElementById('confirmModalCancel');
    const confirmBtn = document.getElementById('confirmModalConfirm');
    if (!overlay || !cancelBtn || !confirmBtn) return resolve(false);
    if (titleEl) titleEl.textContent = 'Отвязать токен?';
    textEl.textContent = `Текущий токен будет удалён. Сервис ${serviceName} перестанет работать до привязки нового токена.`;
    overlay.removeAttribute('hidden');

    const cleanup = () => {
      overlay.setAttribute('hidden', '');
      cancelBtn.removeEventListener('click', onCancel);
      confirmBtn.removeEventListener('click', onConfirm);
      overlay.removeEventListener('click', onBackdropClick);
      if (modal) modal.removeEventListener('click', stopProp);
    };

    const stopProp = (e) => e.stopPropagation();
    const onBackdropClick = (e) => {
      if (e.target === overlay) {
        cleanup();
        resolve(false);
      }
    };

    const onCancel = (e) => {
      e.preventDefault();
      cleanup();
      resolve(false);
    };
    const onConfirm = (e) => {
      e.preventDefault();
      cleanup();
      resolve(true);
    };

    if (modal) modal.addEventListener('click', stopProp);
    overlay.addEventListener('click', onBackdropClick);
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

/** Task 5: empty apiKey + active token = valid (we keep existing key). Uses getEffectiveModelType() for custom provider. */
function isLlmFormValid() {
  const llmType = (document.getElementById('llmType')?.value || '').trim();
  const modelType = getEffectiveModelType();
  const apiKeyEl = document.getElementById('llmApiKey');
  const apiKey = (apiKeyEl?.value || '').trim();
  if (!llmType) return false;
  const hasKey = !!(apiKey || (lastLlm?.isActive && lastLlm?.activeTokenMasked));
  const placeholder = (apiKeyEl?.placeholder || '').trim();
  const hasSavedKeyPlaceholder = !!(placeholder && placeholder !== 'Ключ API');
  const noModelOk = (hasKey || hasSavedKeyPlaceholder);
  if (!modelType && !noModelOk) return false;
  if (llmType.toLowerCase() === 'ollama') return true;
  if (apiKey) return true;
  if (lastLlm?.isActive && lastLlm?.activeTokenMasked) return true;
  return !!hasSavedKeyPlaceholder;
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

/** For custom provider there are no preset models; use text input. Returns true if provider uses custom model input. */
function isCustomModelProvider(providerId) {
  return (providerId || '').toLowerCase() === 'custom';
}

/** Providers that support fetch models from API (OpenAI GET /models, Anthropic GET /v1/models, Google GET /v1beta/models). Perplexity, Yandex: no list API, static list. */
function isOpenAiCompatibleProvider(providerId) {
  const id = (providerId || '').toLowerCase();
  return ['openai', 'anthropic', 'google', 'groq', 'openrouter', 'ollama', 'xai', 'deepseek', 'azure'].includes(id);
}

/**
 * Heuristic: model is reasoning-type by id or display name.
 * Проверяем и id, и display_name (название может быть "O3 Mini", id — с датой).
 */
function isReasoningModel(model) {
  const id = (model && model.id) ? String(model.id).toLowerCase() : '';
  const name = (model && model.display_name) ? String(model.display_name).toLowerCase() : '';
  const s = id + ' ' + name;
  return (
    /^o1[-.]|^o1$|\bo1[-.]|\bo1\b/.test(s) ||
    /^o3|^o3$|\bo3[-.]|\bo3\b/.test(s) ||
    /^o4|^o4$|\bo4[-.]|\bo4\b/.test(s) ||
    /^gpt-5[-.]|^gpt-5$|\bgpt-5\b/.test(s) ||
    /\breasoning\b/.test(s) ||
    /\bthinking\b/.test(s) ||
    /\bdeep.?think\b/.test(s)
  );
}

/** Placeholder model for "save credentials only" (no model selected yet). Used for all providers. */
function getPlaceholderModel(providerId) {
  const prov = getProviderById(providerId);
  if (!prov?.models) return 'gpt-4o';
  const std = prov.models.standard || [];
  const reas = prov.models.reasoning || [];
  return std[0] || reas[0] || 'gpt-4o';
}

/** Fill model select from fetched API list ([{id, display_name?}, ...]). Names as from provider. Splits into standard / reasoning. */
function fillLlmModelSelectFromIds(modelList, selectedModel) {
  const sel = document.getElementById('llmModel');
  if (!sel) return;
  sel.disabled = false;
  sel.innerHTML = '<option value="">— выберите модель —</option>';
  const list = (modelList || []).filter((m) => m && m.id && String(m.id).trim());
  const standard = list.filter((m) => !isReasoningModel(m));
  const reasoning = list.filter(isReasoningModel);
  const label = (m) => (m.display_name && String(m.display_name).trim()) || m.id;
  // Сначала думающие (🧠), потом стандартные — так группа «думающие» лучше видна
  if (reasoning.length) {
    const g = document.createElement('optgroup');
    g.label = 'Reasoning модели (🧠)';
    reasoning.forEach((m) => {
      const o = document.createElement('option');
      o.value = m.id;
      o.textContent = label(m);
      g.appendChild(o);
    });
    sel.appendChild(g);
  }
  if (standard.length) {
    const g = document.createElement('optgroup');
    g.label = 'Стандартные модели';
    standard.forEach((m) => {
      const o = document.createElement('option');
      o.value = m.id;
      o.textContent = label(m);
      g.appendChild(o);
    });
    sel.appendChild(g);
  }
  const allIds = [...reasoning, ...standard].map((m) => m.id);
  if (selectedModel && allIds.includes(selectedModel)) sel.value = selectedModel;
  else if (allIds.length) sel.value = allIds[0];
}

/** Set model select to "no API key" state: disabled, single option with message. */
function setLlmModelSelectNoKey() {
  const sel = document.getElementById('llmModel');
  if (!sel) return;
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Введите API key и сохраните, чтобы загрузить список моделей —</option>';
  sel.value = '';
}

/** Fetch models from API (uses saved creds) and fill model select. Used after save or on load when key present. */
async function fetchLlmModelsAndFill(selectedModel) {
  const sel = document.getElementById('llmModel');
  if (!sel) return;
  try {
    const r = await api('/api/settings/llm/fetch-models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await r.json().catch(() => ({}));
    if (data.error) {
      setLlmModelSelectNoKey();
      return;
    }
    fillLlmModelSelectFromIds(data.models || [], selectedModel || getEffectiveModelType());
  } catch (_) {
    setLlmModelSelectNoKey();
  }
}

/**
 * Fill model select. For all non-custom providers: no API key → disabled + message; with key → list (fetched or static).
 * @param {string} providerId
 * @param {string} selectedModel
 * @param {boolean} [hasApiKey] — has saved/entered API key for this provider (if false, dropdown disabled for any provider)
 */
function fillLlmModelSelect(providerId, selectedModel, hasApiKey = true) {
  const sel = document.getElementById('llmModel');
  const customInput = document.getElementById('llmModelCustom');
  if (!sel) return;
  if (isCustomModelProvider(providerId)) {
    sel.style.display = 'none';
    if (customInput) {
      customInput.style.display = 'block';
      customInput.value = selectedModel || '';
      customInput.placeholder = 'Например: gpt-4o';
    }
    sel.innerHTML = '<option value="">— Custom —</option>';
    sel.value = '';
    return;
  }
  if (customInput) customInput.style.display = 'none';
  sel.style.display = '';
  sel.disabled = false;
  if (!hasApiKey) {
    setLlmModelSelectNoKey();
    return;
  }
  if (isOpenAiCompatibleProvider(providerId)) {
    setLlmModelSelectNoKey();
    return;
  }
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

/** Get effective model type: from select or from custom input when provider is custom. */
function getEffectiveModelType() {
  const llmType = (document.getElementById('llmType')?.value || '').trim();
  if (isCustomModelProvider(llmType)) {
    return (document.getElementById('llmModelCustom')?.value || '').trim();
  }
  return (document.getElementById('llmModel')?.value || '').trim();
}

function updateLlmBaseUrlHint(providerId) {
  const hint = document.getElementById('llmBaseUrlHint');
  if (!hint) return;
  const prov = getProviderById(providerId);
  hint.textContent = prov?.defaultBaseUrl ? `По умолчанию: ${prov.defaultBaseUrl}` : '';
}

function toggleLlmAzureFields(providerId) {
  const block = document.getElementById('llmAzureFields');
  if (!block) return;
  const isAzure = (providerId || '').toLowerCase() === 'azure';
  if (isAzure) {
    block.removeAttribute('hidden');
  } else {
    block.setAttribute('hidden', '');
  }
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
    if (telegramActiveEl) {
      if (tg.isActive === true && tg.activeTokenMasked) {
        telegramActiveEl.removeAttribute('hidden');
        if (telegramActiveValueEl) telegramActiveValueEl.textContent = tg.activeTokenMasked;
      } else {
        telegramActiveEl.setAttribute('hidden', '');
        if (telegramActiveValueEl) telegramActiveValueEl.textContent = '';
      }
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
    const llmHasKey = !!(llm.apiKeyMasked || llm.isActive);
    fillLlmModelSelect(llm.llmType || '', llm.modelType || '', llmHasKey);
    if (llmHasKey && isOpenAiCompatibleProvider(llm.llmType || '')) {
      fetchLlmModelsAndFill(llm.modelType || '');
    }
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
    if (llmActiveEl) {
      if (llm.isActive === true && llm.activeTokenMasked) {
        llmActiveEl.removeAttribute('hidden');
        if (llmActiveValueEl) llmActiveValueEl.textContent = llm.activeTokenMasked;
      } else {
        llmActiveEl.setAttribute('hidden', '');
        if (llmActiveValueEl) llmActiveValueEl.textContent = '';
      }
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
    toggleLlmAzureFields(llm.llmType || '');
    if (llm.llmType === 'azure') {
      const azureEndEl = document.getElementById('llmAzureEndpoint');
      const azureVerEl = document.getElementById('llmAzureApiVersion');
      if (azureEndEl) azureEndEl.value = llm.azureEndpoint || '';
      if (azureVerEl) azureVerEl.value = llm.apiVersion || '';
    }
    updateLlmSaveDisabled();

    // Load service admins
    await loadServiceAdmins();
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
    if (telegramActiveEl) {
      if (tg.isActive === true && tg.activeTokenMasked) {
        telegramActiveEl.removeAttribute('hidden');
        if (telegramActiveValueEl) telegramActiveValueEl.textContent = tg.activeTokenMasked;
      } else {
        telegramActiveEl.setAttribute('hidden', '');
        if (telegramActiveValueEl) telegramActiveValueEl.textContent = '';
      }
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
  const modelType = getEffectiveModelType();
  const systemPrompt = (document.getElementById('llmSystemPrompt')?.value || '').trim() || null;
  const azureEndpoint = (document.getElementById('llmAzureEndpoint')?.value || '').trim() || null;
  const apiVersion = (document.getElementById('llmAzureApiVersion')?.value || '').trim() || null;
  const prov = getProviderById(llmType);
  if (!baseUrl && prov?.defaultBaseUrl) baseUrl = prov.defaultBaseUrl;
  const prev = lastLlm || {};
  const changed = [];
  if (llmType !== (prev.llmType || '')) changed.push('llmType');
  if (apiKey) changed.push('apiKey');
  if (baseUrl !== (prev.baseUrl || '')) changed.push('baseUrl');
  if (modelType !== (prev.modelType || '')) changed.push('modelType');
  if ((systemPrompt || '') !== (prev.systemPrompt || '')) changed.push('systemPrompt');
  if (llmType === 'azure') {
    if ((azureEndpoint || '') !== (prev.azureEndpoint || '')) changed.push('azureEndpoint');
    if ((apiVersion || '') !== (prev.apiVersion || '')) changed.push('apiVersion');
  }
  return { changed, llmType, apiKey, baseUrl, modelType, systemPrompt, azureEndpoint, apiVersion };
}

async function llmSave() {
  let { changed, llmType, apiKey, baseUrl, modelType, systemPrompt, azureEndpoint, apiVersion } = getLlmChangedFields();
  const hasKey = !!(apiKey || (lastLlm?.isActive && lastLlm?.activeTokenMasked));
  const noModelButHasKey = !modelType && hasKey;
  if (noModelButHasKey) {
    modelType = getPlaceholderModel(llmType);
  }

  setFieldError('llmType', 'llmFieldError', '');
  document.getElementById('llmType')?.classList.remove('field-input--error');
  document.getElementById('llmModel')?.classList.remove('field-input--error');
  document.getElementById('llmApiKey')?.classList.remove('field-input--error');

  if (!llmType || (!modelType && !noModelButHasKey)) {
    showToast('Заполните обязательные поля', 'warning');
    setFieldError(llmType ? 'llmModel' : 'llmType', 'llmFieldError', 'Заполните обязательные поля');
    if (!llmType) document.getElementById('llmType')?.classList.add('field-input--error');
    if (!modelType && !noModelButHasKey) document.getElementById('llmModel')?.classList.add('field-input--error');
    return;
  }
  if (!apiKey && llmType.toLowerCase() !== 'ollama' && !(lastLlm.isActive && lastLlm.activeTokenMasked)) {
    showToast('Введите API key', 'warning');
    setFieldError('llmApiKey', 'llmFieldError', 'Введите API key');
    document.getElementById('llmApiKey')?.classList.add('field-input--error');
    return;
  }

  const requiresConnectionCheck = changed.some((f) =>
    ['llmType', 'apiKey', 'baseUrl', 'azureEndpoint', 'apiVersion'].includes(f)
  );
  const onlyModelOrPrompt = changed.length > 0 && !requiresConnectionCheck && (changed.includes('modelType') || changed.includes('systemPrompt'));

  if (changed.length === 0) {
    showToast('Нет изменений', 'success');
    return;
  }

  const btn = document.getElementById('llmSave');
  setButtonLoading(btn, true);
  try {
    if (onlyModelOrPrompt) {
      const patchBody = { modelType, systemPrompt };
      if (llmType === 'azure') {
        patchBody.azureEndpoint = azureEndpoint || undefined;
        patchBody.apiVersion = apiVersion || undefined;
      }
      const r = await api('/api/settings/llm', {
        method: 'PATCH',
        body: JSON.stringify(patchBody),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || r.statusText);
      }
      const data = await r.json();
      lastLlm = { ...data.llm };
      const modelChanged = changed.includes('modelType');
      const promptChanged = changed.includes('systemPrompt');
      const toastMsg = modelChanged && promptChanged
        ? 'Модель и системный промпт обновлены'
        : modelChanged
          ? `Модель изменена на ${modelType}`
          : 'Системный промпт обновлён';
      showToast(toastMsg, 'success');
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
      if (llmActiveEl) {
        if (data.llm?.isActive === true && data.llm?.activeTokenMasked) {
          llmActiveEl.removeAttribute('hidden');
          if (llmActiveValueEl) llmActiveValueEl.textContent = data.llm.activeTokenMasked;
        } else {
          llmActiveEl.setAttribute('hidden', '');
          if (llmActiveValueEl) llmActiveValueEl.textContent = '';
        }
      }
    } else {
      const putBody = {
        llmType,
        apiKey: apiKey || null,
        baseUrl,
        modelType,
        systemPrompt,
      };
      if (llmType === 'azure') {
        putBody.azureEndpoint = azureEndpoint || null;
        putBody.apiVersion = apiVersion || null;
      }
      const r = await api('/api/settings/llm', {
        method: 'PUT',
        body: JSON.stringify(putBody),
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
      if (llmActiveEl) {
        if (data.llm?.isActive === true && data.llm?.activeTokenMasked) {
          llmActiveEl.removeAttribute('hidden');
          if (llmActiveValueEl) llmActiveValueEl.textContent = data.llm.activeTokenMasked;
        } else {
          llmActiveEl.setAttribute('hidden', '');
          if (llmActiveValueEl) llmActiveValueEl.textContent = '';
        }
      }
      if (isOpenAiCompatibleProvider(llmType)) {
        fetchLlmModelsAndFill(modelType);
      } else {
        fillLlmModelSelect(llmType, modelType, true);
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
  const hasApiKey = lastLlm?.llmType === providerId && (lastLlm?.apiKeyMasked || lastLlm?.isActive);
  fillLlmModelSelect(providerId, null, hasApiKey);
  if (hasApiKey && isOpenAiCompatibleProvider(providerId)) {
    fetchLlmModelsAndFill(lastLlm?.modelType || '');
  }
  toggleLlmAzureFields(providerId);
  const errEl = document.getElementById('llmFetchModelsError');
  if (errEl) errEl.textContent = '';
  if ((providerId || '').toLowerCase() === 'azure') {
    const azureVerEl = document.getElementById('llmAzureApiVersion');
    if (azureVerEl && !azureVerEl.value) azureVerEl.value = '2024-02-15-preview';
  }
  updateLlmSaveDisabled();
}

// --- Service admins ---

let serviceAdminsList = [];

async function loadServiceAdmins() {
  try {
    const r = await api('/api/service-admins');
    if (!r.ok) {
      if (r.status === 403) {
        showToast('Требуется Admin key (заголовок X-Admin-Key)', 'warning');
        return;
      }
      throw new Error(r.statusText);
    }
    const data = await r.json();
    serviceAdminsList = data.admins || [];
    renderServiceAdminsList();
  } catch (e) {
    showToast('Ошибка загрузки списка админов: ' + e.message, 'error');
  }
}

function renderServiceAdminsList() {
  const container = document.getElementById('serviceAdminsList');
  const placeholder = document.getElementById('serviceAdminsPlaceholder');
  if (!container) return;

  container.innerHTML = '';
  if (serviceAdminsList.length === 0) {
    if (placeholder) placeholder.removeAttribute('hidden');
    return;
  }
  if (placeholder) placeholder.setAttribute('hidden', '');

  serviceAdminsList.forEach((admin) => {
    const row = renderServiceAdminRow(admin);
    container.appendChild(row);
  });
}

function renderServiceAdminRow(admin) {
  const row = document.createElement('div');
  row.className = 'service-admin-row';
  row.dataset.telegramId = admin.telegram_id;

  const info = document.createElement('div');
  info.className = 'service-admin-info';

  const idEl = document.createElement('span');
  idEl.className = 'service-admin-id';
  idEl.textContent = String(admin.telegram_id);

  const nameEl = document.createElement('span');
  nameEl.className = 'service-admin-name';
  nameEl.textContent = admin.display_name || String(admin.telegram_id);

  info.appendChild(idEl);
  info.appendChild(nameEl);
  row.appendChild(info);

  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'btn btn-link btn-link--danger';
  deleteBtn.textContent = 'Delete';
  deleteBtn.addEventListener('click', () => serviceAdminDelete(admin.telegram_id, admin.display_name || String(admin.telegram_id)));
  row.appendChild(deleteBtn);

  return row;
}

async function serviceAdminAdd() {
  const inputEl = document.getElementById('serviceAdminTelegramId');
  const errorEl = document.getElementById('serviceAdminFieldError');
  if (!inputEl) return;

  const value = (inputEl.value || '').trim();
  setFieldError('serviceAdminTelegramId', 'serviceAdminFieldError', '');

  // Validation
  if (!value) {
    setFieldError('serviceAdminTelegramId', 'serviceAdminFieldError', 'Введите Telegram ID');
    showToast('Введите Telegram ID', 'warning');
    return;
  }

  const telegramId = parseInt(value, 10);
  if (isNaN(telegramId) || telegramId <= 0) {
    setFieldError('serviceAdminTelegramId', 'serviceAdminFieldError', 'Telegram ID должен быть положительным числом');
    showToast('Telegram ID должен быть положительным числом', 'warning');
    return;
  }

  // Check duplicate
  if (serviceAdminsList.some((a) => a.telegram_id === telegramId)) {
    setFieldError('serviceAdminTelegramId', 'serviceAdminFieldError', 'Этот пользователь уже добавлен');
    showToast('Этот пользователь уже добавлен', 'warning');
    return;
  }

  const btn = document.getElementById('serviceAdminAdd');
  setButtonLoading(btn, true);

  try {
    const r = await api('/api/service-admins', {
      method: 'POST',
      body: JSON.stringify({ telegram_id: telegramId }),
    });

    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail || r.statusText || 'Ошибка добавления';
      if (r.status === 409) {
        setFieldError('serviceAdminTelegramId', 'serviceAdminFieldError', 'Этот пользователь уже добавлен');
        showToast('Этот пользователь уже добавлен', 'warning');
      } else {
        setFieldError('serviceAdminTelegramId', 'serviceAdminFieldError', msg);
        showToast('Ошибка: ' + msg, 'error');
      }
      return;
    }

    const admin = await r.json();
    serviceAdminsList.push(admin);
    renderServiceAdminsList();
    inputEl.value = '';
    showToast('Администратор добавлен', 'success');
  } catch (e) {
    showToast('Ошибка добавления: ' + e.message, 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

function confirmDeleteAdmin(displayName) {
  return new Promise((resolve) => {
    const overlay = document.getElementById('confirmModalOverlay');
    const modal = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmModalTitle');
    const textEl = document.getElementById('confirmModalText');
    const cancelBtn = document.getElementById('confirmModalCancel');
    const confirmBtn = document.getElementById('confirmModalConfirm');
    if (!overlay || !cancelBtn || !confirmBtn) return resolve(false);
    if (titleEl) titleEl.textContent = 'Удалить администратора?';
    textEl.textContent = `Удалить пользователя ${displayName} из администраторов?`;
    overlay.removeAttribute('hidden');

    const cleanup = () => {
      overlay.setAttribute('hidden', '');
      cancelBtn.removeEventListener('click', onCancel);
      confirmBtn.removeEventListener('click', onConfirm);
      overlay.removeEventListener('click', onBackdropClick);
      if (modal) modal.removeEventListener('click', stopProp);
    };

    const stopProp = (e) => e.stopPropagation();
    const onBackdropClick = (e) => {
      if (e.target === overlay) {
        cleanup();
        resolve(false);
      }
    };

    const onCancel = (e) => {
      e.preventDefault();
      cleanup();
      resolve(false);
    };
    const onConfirm = (e) => {
      e.preventDefault();
      cleanup();
      resolve(true);
    };

    if (modal) modal.addEventListener('click', stopProp);
    overlay.addEventListener('click', onBackdropClick);
    cancelBtn.addEventListener('click', onCancel);
    confirmBtn.addEventListener('click', onConfirm);
  });
}

async function serviceAdminDelete(telegramId, displayName) {
  const ok = await confirmDeleteAdmin(displayName);
  if (!ok) return;

  const btn = document.querySelector(`.service-admin-row[data-telegram-id="${telegramId}"] .btn-link--danger`);
  if (btn) setButtonLoading(btn, true);

  try {
    const r = await api(`/api/service-admins/${telegramId}`, {
      method: 'DELETE',
    });

    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail || r.statusText || 'Ошибка удаления';
      showToast('Ошибка: ' + msg, 'error');
      return;
    }

    serviceAdminsList = serviceAdminsList.filter((a) => a.telegram_id !== telegramId);
    renderServiceAdminsList();
    showToast('Администратор удалён', 'success');
  } catch (e) {
    showToast('Ошибка удаления: ' + e.message, 'error');
  } finally {
    if (btn) setButtonLoading(btn, false);
  }
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
  document.getElementById('llmModelCustom')?.addEventListener('input', () => {
    setFieldError('llmModel', 'llmFieldError', '');
    updateLlmSaveDisabled();
  });
  document.getElementById('llmApiKey')?.addEventListener('input', () => {
    setFieldError('llmApiKey', 'llmFieldError', '');
    document.getElementById('llmApiKey')?.classList.remove('field-input--error');
    updateLlmSaveDisabled();
  });

  // Service admins
  document.getElementById('serviceAdminAdd')?.addEventListener('click', serviceAdminAdd);
  document.getElementById('serviceAdminTelegramId')?.addEventListener('input', () => {
    setFieldError('serviceAdminTelegramId', 'serviceAdminFieldError', '');
    document.getElementById('serviceAdminTelegramId')?.classList.remove('field-input--error');
  });
  document.getElementById('serviceAdminTelegramId')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      serviceAdminAdd();
    }
  });
});
