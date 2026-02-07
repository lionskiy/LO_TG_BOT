"""CRUD for hr_employees table. Used by hr_service plugin and HR API."""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from api.db import EmployeeModel, SessionLocal, _utc_now

logger = logging.getLogger(__name__)


def _row_to_dict(row: EmployeeModel) -> dict:
    """Convert EmployeeModel to dict with serializable date/decimal."""
    d: Dict[str, Any] = {
        "id": row.id,
        "personal_number": row.personal_number,
        "full_name": row.full_name,
        "email": row.email,
        "jira_worker_id": row.jira_worker_id,
        "position": row.position,
        "mvz": row.mvz,
        "supervisor": row.supervisor,
        "hire_date": row.hire_date.isoformat() if row.hire_date else None,
        "fte": float(row.fte) if row.fte is not None else 1.0,
        "dismissal_date": row.dismissal_date.isoformat() if row.dismissal_date else None,
        "birth_date": row.birth_date.isoformat() if row.birth_date else None,
        "mattermost_username": row.mattermost_username,
        "is_supervisor": bool(row.is_supervisor),
        "is_delivery_manager": bool(row.is_delivery_manager),
        "team": row.team,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    return d


def _parse_date(v: Any) -> Optional[date]:
    """Parse string or date to date or None."""
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v if not isinstance(v, datetime) else v.date()
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def get_employee_by_id(employee_id: int) -> Optional[dict]:
    """Get one employee by primary key. Returns dict or None."""
    with SessionLocal() as session:
        row = session.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
        return _row_to_dict(row) if row else None


def get_employee_by_personal_number(personal_number: str) -> Optional[dict]:
    """Get one employee by personal_number. Returns dict or None."""
    with SessionLocal() as session:
        row = session.query(EmployeeModel).filter(
            EmployeeModel.personal_number == str(personal_number).strip()
        ).first()
        return _row_to_dict(row) if row else None


def get_employee_by_email(email: str) -> Optional[dict]:
    """Get one employee by email. Returns dict or None."""
    with SessionLocal() as session:
        row = session.query(EmployeeModel).filter(
            EmployeeModel.email == str(email).strip()
        ).first()
        return _row_to_dict(row) if row else None


def find_employees_by_name(query: str) -> List[dict]:
    """Find employees by full_name containing query (case-insensitive)."""
    q = str(query).strip()
    if not q:
        return []
    with SessionLocal() as session:
        rows = session.query(EmployeeModel).filter(
            EmployeeModel.full_name.ilike(f"%{q}%")
        ).all()
        return [_row_to_dict(r) for r in rows]


def get_employee(
    query: Optional[str] = None,
    personal_number: Optional[str] = None,
    email: Optional[str] = None,
) -> tuple:
    """
    Get one employee by query (name), personal_number, or email.
    Returns (employee_dict, error_message). If found, error_message is empty.
    If multiple by name, returns (None, "Multiple matches: ...").
    """
    if personal_number and str(personal_number).strip():
        emp = get_employee_by_personal_number(str(personal_number).strip())
        if emp:
            return (emp, "")
        return (None, "Employee not found for this personal number.")
    if email and str(email).strip():
        emp = get_employee_by_email(str(email).strip())
        if emp:
            return (emp, "")
        return (None, "Employee not found for this email.")
    if query and str(query).strip():
        candidates = find_employees_by_name(str(query).strip())
        if not candidates:
            return (None, "Employee not found.")
        if len(candidates) == 1:
            return (candidates[0], "")
        names = ", ".join(c["full_name"] for c in candidates[:10])
        if len(candidates) > 10:
            names += f" and {len(candidates) - 10} more"
        return (None, f"Multiple matches: {names}. Specify personal_number or email.")
    return (None, "Provide query (name), personal_number, or email.")


def list_employees(
    view: str = "all",
    mvz: Optional[str] = None,
    team: Optional[str] = None,
    supervisors_only: bool = False,
    delivery_managers_only: bool = False,
    limit: int = 500,
    offset: int = 0,
) -> List[dict]:
    """
    List employees with optional filters. view: all | supervisors | delivery_managers.
    """
    with SessionLocal() as session:
        q = session.query(EmployeeModel)
        if view == "supervisors" or supervisors_only:
            q = q.filter(EmployeeModel.is_supervisor == True)
        if view == "delivery_managers" or delivery_managers_only:
            q = q.filter(EmployeeModel.is_delivery_manager == True)
        if mvz and str(mvz).strip():
            q = q.filter(EmployeeModel.mvz.ilike(f"%{str(mvz).strip()}%"))
        if team and str(team).strip():
            q = q.filter(EmployeeModel.team.ilike(f"%{str(team).strip()}%"))
        q = q.order_by(EmployeeModel.full_name)
        rows = q.offset(offset).limit(limit).all()
        return [_row_to_dict(r) for r in rows]


def search_employees(
    query: str,
    limit: int = 50,
) -> List[dict]:
    """Search by name, position, mvz, email (any field)."""
    q = str(query).strip()
    if not q:
        return []
    pattern = f"%{q}%"
    with SessionLocal() as session:
        rows = (
            session.query(EmployeeModel)
            .filter(
                or_(
                    EmployeeModel.full_name.ilike(pattern),
                    EmployeeModel.email.ilike(pattern),
                    EmployeeModel.position.ilike(pattern),
                    EmployeeModel.mvz.ilike(pattern),
                    EmployeeModel.team.ilike(pattern),
                )
            )
            .order_by(EmployeeModel.full_name)
            .limit(limit)
            .all()
        )
        return [_row_to_dict(r) for r in rows]


def update_employee(
    employee_id: int,
    updates: dict,
) -> tuple:
    """
    Partially update an employee. updates: dict of field -> value.
    Returns (updated_employee_dict, error_message).
    """
    allowed = {
        "fte", "dismissal_date", "is_supervisor", "is_delivery_manager",
        "team", "mvz", "supervisor", "position", "mattermost_username",
        "jira_worker_id", "birth_date", "hire_date",
    }
    bad = set(updates.keys()) - allowed
    if bad:
        return (None, f"Invalid fields: {', '.join(sorted(bad))}")
    with SessionLocal() as session:
        row = session.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
        if not row:
            return (None, "Employee not found.")
        for key, value in updates.items():
            if key == "fte":
                row.fte = float(value) if value is not None else 1.0
            elif key == "dismissal_date":
                row.dismissal_date = _parse_date(value)
            elif key == "birth_date":
                row.birth_date = _parse_date(value)
            elif key == "hire_date":
                row.hire_date = _parse_date(value)
            elif key == "is_supervisor":
                row.is_supervisor = bool(value)
            elif key == "is_delivery_manager":
                row.is_delivery_manager = bool(value)
            elif key in ("team", "mvz", "supervisor", "position", "mattermost_username", "jira_worker_id"):
                setattr(row, key, str(value).strip() if value is not None and str(value).strip() else None)
        row.updated_at = _utc_now()
        session.commit()
        session.refresh(row)
        return (_row_to_dict(row), "")


def create_employee(
    personal_number: str,
    full_name: str,
    email: str,
    position: Optional[str] = None,
    mvz: Optional[str] = None,
    supervisor: Optional[str] = None,
    hire_date: Optional[date] = None,
    mattermost_username: Optional[str] = None,
) -> dict:
    """Insert a new employee. Defaults: fte=1, is_supervisor=False, is_delivery_manager=False."""
    with SessionLocal() as session:
        row = EmployeeModel(
            personal_number=str(personal_number).strip(),
            full_name=str(full_name).strip(),
            email=str(email).strip(),
            position=(position and str(position).strip()) or None,
            mvz=(mvz and str(mvz).strip()) or None,
            supervisor=(supervisor and str(supervisor).strip()) or None,
            hire_date=hire_date,
            fte=Decimal("1"),
            mattermost_username=(mattermost_username and str(mattermost_username).strip()) or (email and str(email).strip()) or None,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_dict(row)


def employee_exists_by_personal_number(personal_number: str) -> bool:
    """Check if an employee with this personal_number already exists."""
    with SessionLocal() as session:
        return (
            session.query(EmployeeModel)
            .filter(EmployeeModel.personal_number == str(personal_number).strip())
            .first()
            is not None
        )


def set_employee_jira_worker_id(employee_id: int, jira_worker_id: str) -> bool:
    """Set jira_worker_id for an employee. Returns True if updated."""
    with SessionLocal() as session:
        row = session.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
        if not row:
            return False
        row.jira_worker_id = str(jira_worker_id).strip() or None
        row.updated_at = _utc_now()
        session.commit()
        return True
