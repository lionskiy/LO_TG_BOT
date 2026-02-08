"""REST API for admin «Работа с БД»: employees list, get, PATCH, import. Protected by X-Admin-Key."""
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from api.employees_repository import (
    get_employee_by_id,
    list_employees,
    update_employee,
)
from plugins.hr_service.import_excel import import_employees_from_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hr", tags=["hr"])
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()


def _require_admin(x_admin_key: str = Header(None, alias="X-Admin-Key")) -> None:
    if ADMIN_API_KEY and (not x_admin_key or x_admin_key != ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/employees")
async def get_employees(
    view: str = "all",
    _: None = Depends(_require_admin),
):
    """
    List employees. view: all | supervisors | delivery_managers.
    """
    if view not in ("all", "supervisors", "delivery_managers"):
        raise HTTPException(status_code=400, detail="view must be all, supervisors, or delivery_managers")
    items = list_employees(view=view)
    return items


@router.get("/employees/{employee_id}")
async def get_employee(
    employee_id: int,
    _: None = Depends(_require_admin),
):
    """Get one employee by id."""
    emp = get_employee_by_id(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.patch("/employees/{employee_id}")
async def patch_employee(
    employee_id: int,
    body: dict,
    _: None = Depends(_require_admin),
):
    """Partial update of employee fields (for cell edit in admin)."""
    if not body:
        raise HTTPException(status_code=400, detail="Body required")
    updated, err = update_employee(employee_id, body)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return updated


@router.post("/import")
async def hr_import(
    file: UploadFile = File(...),
    _: None = Depends(_require_admin),
):
    """
    Import employees from Excel (.xlsx/.xls). Sheets ДДЖ and Инфоком.
    Returns { added_count, added_names, errors, enrichment_errors }.
    """
    name = (file.filename or "").lower()
    if not name.endswith(".xlsx") and not name.endswith(".xls"):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx and .xls files are supported",
        )
    suffix = Path(name).suffix or ".xlsx"
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="hr_import_")
        os.close(fd)
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        result = import_employees_from_file(tmp_path)
        if isinstance(result, str) and result.startswith("Error:"):
            raise HTTPException(status_code=400, detail=result)
        return result
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.debug("Cleanup temp %s: %s", tmp_path, e)
