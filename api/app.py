"""FastAPI application for admin settings API."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from api.db import CONNECTION_STATUS_SUCCESS, init_db
from api.llm_providers import get_default_base_url, PROVIDERS_LIST
from api.llm_test import test_llm_connection
from api.settings_repository import (
    get_llm_settings,
    get_telegram_settings,
    save_llm_settings,
    save_telegram_settings,
    set_llm_active,
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


@app.post("/api/settings/telegram/activate")
def telegram_activate():
    """Run connection test; if success, mark saved Telegram settings as active."""
    status, message = test_telegram_connection()
    activated = status == CONNECTION_STATUS_SUCCESS
    set_telegram_active(activated)
    return {"activated": activated, "message": message}


@app.post("/api/settings/llm/test")
def llm_test():
    """Test LLM provider connection. Uses saved settings from DB."""
    status, message = test_llm_connection()
    return {"status": status, "message": message}


@app.put("/api/settings/llm")
def put_llm_settings(body: dict):
    """
    Save LLM block. Validate llmType, apiKey (optional for ollama), modelType.
    Base URL default from provider if empty. Save, run test, set active if success.
    """
    llm_type = (body.get("llmType") or "").strip()
    api_key = (body.get("apiKey") or "").strip() or None
    base_url = (body.get("baseUrl") or "").strip()
    model_type = (body.get("modelType") or "").strip()
    system_prompt = (body.get("systemPrompt") or "").strip() or None
    if not llm_type:
        raise HTTPException(status_code=400, detail="LLM type is required")
    if not model_type:
        raise HTTPException(status_code=400, detail="Model type is required")
    if not api_key and llm_type.lower() != "ollama":
        raise HTTPException(status_code=400, detail="API key is required")
    if not base_url:
        base_url = get_default_base_url(llm_type) or ""
    save_llm_settings(
        llm_type=llm_type,
        api_key=api_key,
        base_url=base_url,
        model_type=model_type,
        system_prompt=system_prompt,
        connection_status="not_configured",
        is_active=False,
    )
    status, _message = test_llm_connection()
    applied = status == CONNECTION_STATUS_SUCCESS
    set_llm_active(applied)
    settings = get_llm_settings()
    return {"llm": settings, "applied": applied}


@app.post("/api/settings/llm/activate")
def llm_activate():
    """Run connection test; if success, mark saved LLM settings as active."""
    status, message = test_llm_connection()
    activated = status == CONNECTION_STATUS_SUCCESS
    set_llm_active(activated)
    return {"activated": activated, "message": message}


@app.get("/api/settings/llm/providers")
def get_llm_providers():
    """Return list of LLM providers with default base URLs and model lists (standard + reasoning)."""
    return {"providers": PROVIDERS_LIST}
