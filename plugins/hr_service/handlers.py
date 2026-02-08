"""
HR Service plugin: one tool 'hr' with action dispatch.
Actions: get_employee, list_employees, search_employees, update_employee, import_employees.
Error contract: "Error: ..." string (DOCUMENTATION_AUDIT).
Write actions (update_employee, import_employees) require service admin when called from bot.
"""
import json
import logging
from typing import Any, Optional

from tools.base import get_current_context


def _is_service_admin_from_context() -> bool:
    """True if current tool context has telegram_id and it is a service admin."""
    ctx = get_current_context()
    if not ctx or ctx.telegram_id is None:
        return False
    try:
        from api.service_admins_repository import is_service_admin
        return is_service_admin(ctx.telegram_id)
    except Exception:
        return False


from api.employees_repository import (
    get_employee as repo_get_employee,
    list_employees as repo_list_employees,
    search_employees as repo_search_employees,
    update_employee as repo_update_employee,
)

logger = logging.getLogger(__name__)

PLUGIN_ID = "hr_service"


def _err(msg: str) -> str:
    """Standard error response for plugin."""
    return f"Error: {msg}"


async def hr_dispatch(
    action: str,
    query: Optional[str] = None,
    mvz: Optional[str] = None,
    team: Optional[str] = None,
    supervisors_only: Optional[bool] = None,
    delivery_managers_only: Optional[bool] = None,
    personal_number: Optional[str] = None,
    updates: Optional[dict] = None,
    file_path: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Single entry point for HR tool. Dispatches by action.
    """
    action = (action or "").strip().lower()
    if not action:
        return _err("action is required")

    if action == "get_employee":
        # If query looks like email, pass as email; otherwise as name search
        email_arg = (query if (query and "@" in str(query)) else None) or None
        name_query = query if not email_arg else None
        emp, err = repo_get_employee(
            query=name_query,
            personal_number=personal_number,
            email=email_arg,
        )
        if err:
            return _err(err)
        return json.dumps(emp, ensure_ascii=False, indent=2)

    if action == "list_employees":
        view = "all"
        if supervisors_only:
            view = "supervisors"
        elif delivery_managers_only:
            view = "delivery_managers"
        items = repo_list_employees(
            view=view,
            mvz=mvz,
            team=team,
            supervisors_only=bool(supervisors_only),
            delivery_managers_only=bool(delivery_managers_only),
        )
        return json.dumps(items, ensure_ascii=False, indent=2)

    if action == "search_employees":
        if not query or not str(query).strip():
            return _err("query is required for search_employees")
        items = repo_search_employees(query=str(query).strip())
        return json.dumps(items, ensure_ascii=False, indent=2)

    if action == "update_employee":
        if not _is_service_admin_from_context():
            return _err("Only service administrators can update employee data.")
        if not updates and not kwargs:
            return _err("updates (or fields) required for update_employee")
        payload = dict(updates) if updates else {}
        payload.update({k: v for k, v in kwargs.items() if v is not None and k != "action"})
        if not payload:
            return _err("No fields to update.")
        # Resolve employee by personal_number or query (name)
        emp_id = None
        if personal_number and str(personal_number).strip():
            from api.employees_repository import get_employee_by_personal_number
            e = get_employee_by_personal_number(str(personal_number).strip())
            if e:
                emp_id = e["id"]
        if emp_id is None and query and str(query).strip():
            from api.employees_repository import find_employees_by_name
            candidates = find_employees_by_name(str(query).strip())
            if len(candidates) == 1:
                emp_id = candidates[0]["id"]
            elif len(candidates) > 1:
                names = ", ".join(c["full_name"] for c in candidates[:5])
                return _err(f"Multiple matches: {names}. Specify personal_number.")
        if emp_id is None:
            return _err("Employee not found. Use query (name) or personal_number.")
        updated, err = repo_update_employee(employee_id=emp_id, updates=payload)
        if err:
            return _err(err)
        return json.dumps(updated, ensure_ascii=False, indent=2)

    if action == "import_employees":
        if not _is_service_admin_from_context():
            return _err("Only service administrators can import employees.")
        if not file_path or not str(file_path).strip():
            return _err("file_path is required for import_employees (path to Excel file).")
        from plugins.hr_service.import_excel import import_employees_from_file
        result = import_employees_from_file(str(file_path).strip())
        if isinstance(result, str) and result.startswith("Error:"):
            return result
        return json.dumps(result, ensure_ascii=False, indent=2)

    return _err(f"Unknown action: {action}")


# Legacy alias for loader (handler name from manifest)
__all__ = ["hr_dispatch"]
