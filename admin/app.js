/**
 * Admin panel: load settings, Telegram block (Retry, Save), toasts, auto-check.
 */

const TELEGRAM_DEFAULT_BASE_URL = 'https://api.telegram.org';
const STATUS_CHECK_INTERVAL_MS = 10000;

let telegramCheckTimer = null;

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

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
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
  } catch (e) {
    showToast('Ошибка загрузки настроек: ' + e.message, 'error');
  }
}

async function telegramTest() {
  setTelegramChecking();
  document.getElementById('telegramRetry').disabled = true;
  try {
    const r = await api('/api/settings/telegram/test', { method: 'POST' });
    const data = await r.json();
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
    document.getElementById('telegramRetry').disabled = false;
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
  const token = document.getElementById('telegramToken').value.trim();
  let baseUrl = document.getElementById('telegramBaseUrl').value.trim();
  if (!baseUrl) baseUrl = TELEGRAM_DEFAULT_BASE_URL;

  if (!token) {
    showToast('Заполните обязательные поля', 'warning');
    document.getElementById('telegramToken').classList.add('field-input--error');
    return;
  }
  document.getElementById('telegramToken').classList.remove('field-input--error');

  const btn = document.getElementById('telegramSave');
  btn.disabled = true;
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
});
