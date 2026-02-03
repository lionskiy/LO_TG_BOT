"""FastAPI application for admin settings API."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from api.db import CONNECTION_STATUS_SUCCESS, init_db
from api.settings_repository import (
    get_llm_settings,
    get_telegram_settings,
    save_telegram_settings,
    set_telegram_active,
)
from api.telegram_test import test_telegram_connection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    init_db()
    yield
    # Shutdown: nothing to close for SQLite in-process


app = FastAPI(title="LO_TG_BOT Admin API", lifespan=lifespan)


@app.get("/api/settings")
def get_settings():
    """Return all settings (Telegram and LLM). Secrets are masked (last 5 chars)."""
    return {
        "telegram": get_telegram_settings(),
        "llm": get_llm_settings(),
    }


@app.post("/api/settings/telegram/test")
def telegram_test():
    """Test Telegram Bot API connection (getMe). Uses saved settings from DB."""
    status, message = test_telegram_connection()
    return {"status": status, "message": message}


@app.put("/api/settings/telegram")
def put_telegram_settings(body: dict):
    """
    Save Telegram block. Validate (accessToken required), save, run test.
    If test success, mark active. Returns saved settings and applied flag.
    """
    access_token = (body.get("accessToken") or "").strip() or None
    base_url = (body.get("baseUrl") or "").strip() or None
    if not access_token:
        raise HTTPException(status_code=400, detail="Access Token is required")
    # Save with temporary status; test will update it
    save_telegram_settings(
        access_token=access_token,
        base_url=base_url,
        connection_status="not_configured",
        is_active=False,
    )
    status, _message = test_telegram_connection()
    applied = status == CONNECTION_STATUS_SUCCESS
    if applied:
        set_telegram_active(True)
    else:
        set_telegram_active(False)
    # Re-fetch to get updated status and lastChecked
    settings = get_telegram_settings()
    return {"telegram": settings, "applied": applied}
