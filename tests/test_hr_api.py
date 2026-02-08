"""Tests for HR API and employees repository."""
import os
import tempfile

import pytest

_test_db = os.path.join(tempfile.gettempdir(), "lo_tg_bot_test_hr.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
os.environ["SETTINGS_ENCRYPTION_KEY"] = "zOkTsCorSklBG_KtNc6s-B_5Mz5HkuDBE5ncOg8yU8Q="


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.app import app
    from api.db import init_db
    init_db()
    return TestClient(app)


def test_hr_employees_list_empty(client):
    """GET /api/hr/employees returns empty list when no employees."""
    r = client.get("/api/hr/employees")
    assert r.status_code == 200
    assert r.json() == []


def test_hr_employees_list_views(client):
    """GET /api/hr/employees?view=supervisors works."""
    r = client.get("/api/hr/employees?view=supervisors")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_hr_employee_not_found(client):
    """GET /api/hr/employees/99999 returns 404."""
    r = client.get("/api/hr/employees/99999")
    assert r.status_code == 404


def test_employees_repository_create_and_get():
    """Create employee via repository, get by id and by personal_number."""
    os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
    from api.db import init_db
    from api.employees_repository import (
        create_employee,
        get_employee_by_id,
        get_employee_by_personal_number,
        get_employee,
        list_employees,
    )
    init_db()
    created = create_employee(
        personal_number="T001",
        full_name="Test User",
        email="test@example.com",
    )
    assert created["id"]
    assert created["personal_number"] == "T001"
    assert created["full_name"] == "Test User"
    assert created["email"] == "test@example.com"
    assert created["fte"] == 1.0
    by_id = get_employee_by_id(created["id"])
    assert by_id["personal_number"] == "T001"
    by_pn = get_employee_by_personal_number("T001")
    assert by_pn["full_name"] == "Test User"
    emp, err = get_employee(query="Test User")
    assert err == ""
    assert emp["email"] == "test@example.com"
    items = list_employees(view="all")
    assert len(items) >= 1
    assert any(r["personal_number"] == "T001" for r in items)
