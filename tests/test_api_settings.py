"""Tests for GET /api/settings and settings API."""
import os
import tempfile

import pytest

# Set before any api import
_test_db = os.path.join(tempfile.gettempdir(), "lo_tg_bot_test_settings.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
# Required for save_telegram_settings/save_llm_settings (encryption)
os.environ["SETTINGS_ENCRYPTION_KEY"] = "zOkTsCorSklBG_KtNc6s-B_5Mz5HkuDBE5ncOg8yU8Q="


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.app import app
    from api.db import init_db
    init_db()
    return TestClient(app)


def test_get_settings_empty(client):
    """GET /api/settings returns telegram and llm blocks with defaults when empty."""
    from api.settings_repository import clear_llm_settings, clear_telegram_settings
    clear_telegram_settings()
    clear_llm_settings()
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert "telegram" in data
    assert "llm" in data
    tg = data["telegram"]
    assert tg["accessToken"] is None
    assert tg["accessTokenMasked"] == ""
    assert tg["baseUrl"] == "https://api.telegram.org"
    assert tg["connectionStatus"] == "not_configured"
    assert tg["isActive"] is False
    llm = data["llm"]
    assert llm["llmType"] is None
    assert llm["apiKey"] is None
    assert llm["apiKeyMasked"] == ""
    assert llm["connectionStatus"] == "not_configured"
    assert llm["isActive"] is False


def test_telegram_test_not_configured(client):
    """POST /api/settings/telegram/test returns not_configured when no token saved."""
    from api.settings_repository import clear_telegram_settings
    clear_telegram_settings()
    r = client.post("/api/settings/telegram/test")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "not_configured"
    assert "message" in data


def test_put_telegram_validation(client):
    """PUT /api/settings/telegram returns 400 when accessToken is missing."""
    r = client.put("/api/settings/telegram", json={"baseUrl": "https://api.telegram.org"})
    assert r.status_code == 400
    assert "required" in r.json().get("detail", "").lower() or "token" in r.json().get("detail", "").lower()


def test_put_telegram_save_and_test(client):
    """PUT /api/settings/telegram saves and runs test; invalid token -> applied false."""
    r = client.put(
        "/api/settings/telegram",
        json={"accessToken": "invalid_token_12345", "baseUrl": "https://api.telegram.org"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "telegram" in data
    assert data["applied"] is False
    assert data["telegram"]["accessTokenMasked"] == "...12345"
    assert data["telegram"]["connectionStatus"] == "failed"


def test_telegram_activate_not_configured(client):
    """POST /api/settings/telegram/activate returns activated false when no token."""
    from api.settings_repository import clear_telegram_settings
    clear_telegram_settings()
    r = client.post("/api/settings/telegram/activate")
    assert r.status_code == 200
    assert r.json().get("activated") is False


def test_llm_test_not_configured(client):
    """POST /api/settings/llm/test returns not_configured when no LLM saved."""
    from api.settings_repository import clear_llm_settings
    clear_llm_settings()
    r = client.post("/api/settings/llm/test")
    assert r.status_code == 200
    assert r.json().get("status") == "not_configured"


def test_put_llm_validation(client):
    """PUT /api/settings/llm returns 400 when llmType or modelType missing."""
    from api.settings_repository import clear_llm_settings
    clear_llm_settings()
    r = client.put(
        "/api/settings/llm",
        json={"apiKey": "sk-x", "baseUrl": "https://api.openai.com/v1"},
    )
    assert r.status_code == 400
    r2 = client.put(
        "/api/settings/llm",
        json={"llmType": "openai", "apiKey": "sk-x"},
    )
    assert r2.status_code == 400
