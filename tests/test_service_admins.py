"""Tests for service admins API and repository."""
import os
import tempfile

import pytest

# Set before any api import
_test_db = os.path.join(tempfile.gettempdir(), "lo_tg_bot_test_service_admins.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
# Required for encryption (if needed for other settings)
os.environ["SETTINGS_ENCRYPTION_KEY"] = "zOkTsCorSklBG_KtNc6s-B_5Mz5HkuDBE5ncOg8yU8Q="


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.app import app
    from api.db import init_db
    init_db()
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Headers with admin key for protected endpoints."""
    os.environ["ADMIN_API_KEY"] = "test_admin_key_123"
    return {"X-Admin-Key": "test_admin_key_123"}


def test_list_service_admins_empty(client, admin_headers):
    """GET /api/service-admins returns empty list when no admins."""
    r = client.get("/api/service-admins", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["admins"] == []
    assert data["total"] == 0


def test_list_service_admins_requires_auth(client):
    """GET /api/service-admins returns 403 without admin key when ADMIN_API_KEY is set."""
    import api.app
    # Set ADMIN_API_KEY directly on the module since it's read at import time
    original_key = api.app.ADMIN_API_KEY
    try:
        api.app.ADMIN_API_KEY = "test_key"
        r = client.get("/api/service-admins")
        assert r.status_code == 403
    finally:
        api.app.ADMIN_API_KEY = original_key


def test_add_service_admin(client, admin_headers):
    """POST /api/service-admins creates admin with valid telegram_id."""
    r = client.post("/api/service-admins", json={"telegram_id": 123456789}, headers=admin_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["telegram_id"] == 123456789
    assert data["is_active"] is True
    assert "display_name" in data
    assert data["display_name"] == "123456789"  # No profile, so ID as display_name


def test_add_service_admin_duplicate(client, admin_headers):
    """POST /api/service-admins returns 409 for duplicate telegram_id."""
    client.post("/api/service-admins", json={"telegram_id": 999888777}, headers=admin_headers)
    r = client.post("/api/service-admins", json={"telegram_id": 999888777}, headers=admin_headers)
    assert r.status_code == 409
    assert "already" in r.json()["detail"].lower()


def test_add_service_admin_invalid_id(client, admin_headers):
    """POST /api/service-admins returns 422 for invalid telegram_id (negative or zero)."""
    r = client.post("/api/service-admins", json={"telegram_id": 0}, headers=admin_headers)
    assert r.status_code == 422
    r2 = client.post("/api/service-admins", json={"telegram_id": -1}, headers=admin_headers)
    assert r2.status_code == 422


def test_get_service_admin(client, admin_headers):
    """GET /api/service-admins/{telegram_id} returns admin."""
    client.post("/api/service-admins", json={"telegram_id": 111222333}, headers=admin_headers)
    r = client.get("/api/service-admins/111222333", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["telegram_id"] == 111222333


def test_get_service_admin_not_found(client, admin_headers):
    """GET /api/service-admins/{telegram_id} returns 404 when not found."""
    r = client.get("/api/service-admins/999999999", headers=admin_headers)
    assert r.status_code == 404


def test_delete_service_admin(client, admin_headers):
    """DELETE /api/service-admins/{telegram_id} removes admin."""
    client.post("/api/service-admins", json={"telegram_id": 444555666}, headers=admin_headers)
    r = client.delete("/api/service-admins/444555666", headers=admin_headers)
    assert r.status_code == 204
    # Verify deleted
    r2 = client.get("/api/service-admins/444555666", headers=admin_headers)
    assert r2.status_code == 404


def test_delete_service_admin_not_found(client, admin_headers):
    """DELETE /api/service-admins/{telegram_id} returns 404 when not found."""
    r = client.delete("/api/service-admins/888777666", headers=admin_headers)
    assert r.status_code == 404


def test_list_service_admins_after_add(client, admin_headers):
    """GET /api/service-admins returns all added admins."""
    client.post("/api/service-admins", json={"telegram_id": 100}, headers=admin_headers)
    client.post("/api/service-admins", json={"telegram_id": 200}, headers=admin_headers)
    r = client.get("/api/service-admins", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    ids = {a["telegram_id"] for a in data["admins"]}
    assert ids == {100, 200}


# --- Repository tests ---


def test_repository_get_all_empty():
    """Repository get_all_service_admins returns empty list."""
    from api.service_admins_repository import get_all_service_admins
    from api.db import init_db
    init_db()
    admins = get_all_service_admins()
    assert admins == []


def test_repository_create_admin():
    """Repository create_service_admin creates admin."""
    from api.service_admins_repository import create_service_admin, get_all_service_admins
    from api.db import init_db
    init_db()
    admin, warning = create_service_admin(555666777)
    assert admin.telegram_id == 555666777
    assert admin.is_active is True
    assert admin.display_name == "555666777"  # No profile
    # Check in list
    all_admins = get_all_service_admins()
    assert len(all_admins) == 1
    assert all_admins[0].telegram_id == 555666777


def test_repository_create_duplicate():
    """Repository create_service_admin raises ValueError for duplicate."""
    from api.service_admins_repository import create_service_admin
    from api.db import init_db
    init_db()
    create_service_admin(777888999)
    with pytest.raises(ValueError, match="already a service admin"):
        create_service_admin(777888999)


def test_repository_get_by_telegram_id():
    """Repository get_service_admin_by_telegram_id finds admin."""
    from api.service_admins_repository import (
        create_service_admin,
        get_service_admin_by_telegram_id,
    )
    from api.db import init_db
    init_db()
    create_service_admin(333444555)
    admin = get_service_admin_by_telegram_id(333444555)
    assert admin is not None
    assert admin.telegram_id == 333444555
    # Not found
    admin2 = get_service_admin_by_telegram_id(999999999)
    assert admin2 is None


def test_repository_delete():
    """Repository delete_service_admin removes admin."""
    from api.service_admins_repository import (
        create_service_admin,
        delete_service_admin,
        get_service_admin_by_telegram_id,
    )
    from api.db import init_db
    init_db()
    create_service_admin(222333444)
    deleted = delete_service_admin(222333444)
    assert deleted is True
    admin = get_service_admin_by_telegram_id(222333444)
    assert admin is None
    # Delete non-existent
    deleted2 = delete_service_admin(999999999)
    assert deleted2 is False


def test_repository_is_service_admin():
    """Repository is_service_admin checks correctly."""
    from api.service_admins_repository import (
        create_service_admin,
        delete_service_admin,
        is_service_admin,
    )
    from api.db import init_db
    init_db()
    assert is_service_admin(111222333) is False
    create_service_admin(111222333)
    assert is_service_admin(111222333) is True
    delete_service_admin(111222333)
    assert is_service_admin(111222333) is False


def test_repository_build_display_name():
    """Repository _build_display_name prioritizes correctly."""
    from api.service_admins_repository import _build_display_name
    # First + last name
    assert _build_display_name({"first_name": "Иван", "last_name": "Петров"}, 123) == "Иван Петров"
    # Only first name
    assert _build_display_name({"first_name": "Иван"}, 123) == "Иван"
    # Username
    assert _build_display_name({"username": "john_doe"}, 123) == "@john_doe"
    # Fallback to ID
    assert _build_display_name({}, 123) == "123"
    assert _build_display_name(None, 456) == "456"
