"""Tests for GET /api/settings and settings API."""
import os
import tempfile

import pytest

# Set before any api import so one engine/sqlite file is used for all connections
_test_db = os.path.join(tempfile.gettempdir(), "lo_tg_bot_test_settings.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.app import app
    from api.db import init_db
    init_db()
    return TestClient(app)


def test_get_settings_empty(client):
    """GET /api/settings returns telegram and llm blocks with defaults when empty."""
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
