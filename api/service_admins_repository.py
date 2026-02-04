"""Service admins: CRUD and Telegram profile fetch. Sync API to match settings_repository."""
import logging
from datetime import datetime
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.db import SessionLocal, ServiceAdminModel
from api.settings_repository import get_telegram_credentials_for_test

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


# --- Pydantic schemas ---


class ServiceAdminCreate(BaseModel):
    """Request body for adding a service admin."""

    telegram_id: int

    @field_validator("telegram_id")
    @classmethod
    def telegram_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("telegram_id must be a positive integer")
        return v


class ServiceAdminResponse(BaseModel):
    """Single service admin for API response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    display_name: str
    is_active: bool
    created_at: datetime


class ServiceAdminList(BaseModel):
    """List of service admins for API response."""

    admins: list[ServiceAdminResponse]
    total: int


# --- Helpers ---


def _fetch_telegram_profile(telegram_id: int) -> Optional[dict[str, Any]]:
    """Get user profile via Telegram Bot API getChat. Returns result dict or None."""
    creds = get_telegram_credentials_for_test()
    if not creds:
        return None
    base = (creds.get("base_url") or "").strip().rstrip("/")
    token = (creds.get("access_token") or "").strip()
    if not base or not token:
        return None
    url = f"{base}/bot{token}/getChat"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(url, params={"chat_id": telegram_id})
        if r.status_code != 200:
            logger.debug("getChat telegram_id=%s status=%s", telegram_id, r.status_code)
            return None
        data = r.json()
        if isinstance(data, dict) and data.get("ok") is True and "result" in data:
            return data["result"]
    except Exception as e:
        logger.warning("getChat telegram_id=%s failed: %s", telegram_id, e)
    return None


def _build_display_name(profile: Optional[dict[str, Any]], telegram_id: int) -> str:
    """Build display name: first_name+last_name > first_name > @username > telegram_id."""
    if not profile:
        return str(telegram_id)
    first = (profile.get("first_name") or "").strip()
    last = (profile.get("last_name") or "").strip()
    username = (profile.get("username") or "").strip()
    if first and last:
        return f"{first} {last}"
    if first:
        return first
    if username:
        return f"@{username}"
    return str(telegram_id)


def _row_to_response(row: ServiceAdminModel) -> ServiceAdminResponse:
    """Map DB row to API response. display_name never None for API."""
    display = (row.display_name or "").strip() or str(row.telegram_id)
    return ServiceAdminResponse(
        id=row.id,
        telegram_id=row.telegram_id,
        first_name=row.first_name,
        last_name=row.last_name,
        username=row.username,
        display_name=display,
        is_active=row.is_active,
        created_at=row.created_at,
    )


# --- Public API ---


def get_all_service_admins() -> list[ServiceAdminResponse]:
    """Return all active service admins, newest first."""
    with SessionLocal() as session:
        rows = (
            session.query(ServiceAdminModel)
            .filter(ServiceAdminModel.is_active.is_(True))
            .order_by(ServiceAdminModel.created_at.desc())
            .all()
        )
        return [_row_to_response(r) for r in rows]


def get_service_admin_by_telegram_id(telegram_id: int) -> Optional[ServiceAdminResponse]:
    """Return one active service admin by telegram_id or None."""
    with SessionLocal() as session:
        row = (
            session.query(ServiceAdminModel)
            .filter(
                ServiceAdminModel.telegram_id == telegram_id,
                ServiceAdminModel.is_active.is_(True),
            )
            .first()
        )
        return _row_to_response(row) if row else None


def create_service_admin(telegram_id: int) -> tuple[ServiceAdminResponse, Optional[str]]:
    """
    Create a service admin. Fetch profile from Telegram if possible.
    Returns (admin_response, warning_message or None).
    Raises ValueError if telegram_id already exists (duplicate).
    """
    with SessionLocal() as session:
        existing = (
            session.query(ServiceAdminModel)
            .filter(ServiceAdminModel.telegram_id == telegram_id)
            .first()
        )
        if existing:
            raise ValueError(f"User with telegram_id {telegram_id} is already a service admin")

        profile = _fetch_telegram_profile(telegram_id)
        display_name = _build_display_name(profile, telegram_id)
        now = datetime.utcnow()

        row = ServiceAdminModel(
            telegram_id=telegram_id,
            first_name=profile.get("first_name") if profile else None,
            last_name=profile.get("last_name") if profile else None,
            username=profile.get("username") if profile else None,
            display_name=display_name,
            role="service_admin",
            is_active=True,
            profile_updated_at=now if profile else None,
        )
        session.add(row)
        try:
            session.commit()
            session.refresh(row)
        except IntegrityError:
            session.rollback()
            raise ValueError(f"User with telegram_id {telegram_id} is already a service admin") from None

        warning = None
        if not profile:
            warning = "Profile data unavailable. Will be updated when user interacts with bot."

        return _row_to_response(row), warning


def delete_service_admin(telegram_id: int) -> bool:
    """Remove service admin by telegram_id. Returns True if deleted, False if not found."""
    with SessionLocal() as session:
        row = (
            session.query(ServiceAdminModel)
            .filter(ServiceAdminModel.telegram_id == telegram_id)
            .first()
        )
        if not row:
            return False
        session.delete(row)
        session.commit()
        return True


def refresh_service_admin_profile(telegram_id: int) -> Optional[ServiceAdminResponse]:
    """Update profile from Telegram getChat. Returns updated admin or None if not found."""
    with SessionLocal() as session:
        row = (
            session.query(ServiceAdminModel)
            .filter(ServiceAdminModel.telegram_id == telegram_id)
            .first()
        )
        if not row:
            return None

        profile = _fetch_telegram_profile(telegram_id)
        if profile:
            row.first_name = profile.get("first_name")
            row.last_name = profile.get("last_name")
            row.username = profile.get("username")
            row.display_name = _build_display_name(profile, telegram_id)
            row.profile_updated_at = datetime.utcnow()
            row.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(row)

        return _row_to_response(row)


def is_service_admin(telegram_id: int) -> bool:
    """Return True if telegram_id is an active service admin."""
    with SessionLocal() as session:
        row = (
            session.query(ServiceAdminModel)
            .filter(
                ServiceAdminModel.telegram_id == telegram_id,
                ServiceAdminModel.is_active.is_(True),
            )
            .first()
        )
        return row is not None
