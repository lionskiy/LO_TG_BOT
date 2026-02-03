"""FastAPI application for admin settings API."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from api.db import CONNECTION_STATUS_SUCCESS, init_db
from api.llm_providers import (
    OPENAI_KNOWN_MODEL_IDS,
    fetch_models_anthropic,
    fetch_models_from_api,
    fetch_models_google,
    get_default_base_url,
    PROVIDERS_LIST,
)
from api.llm_test import test_llm_connection
from api.bot_runner import restart_bot, start_bot, stop_bot
from api.settings_repository import (
    clear_llm_settings,
    clear_llm_token,
    clear_telegram_settings,
    clear_telegram_token,
    get_llm_credentials_for_test,
    get_llm_settings,
    get_telegram_credentials_for_test,
    get_telegram_settings,
    get_telegram_settings_decrypted,
    save_llm_settings,
    save_telegram_settings,
    set_llm_active,
    set_telegram_active,
    update_llm_model_and_prompt,
)
from api.telegram_test import test_telegram_connection, test_telegram_connection_async

logger = logging.getLogger(__name__)

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()


def _require_admin(x_admin_key: str = Header(None, alias="X-Admin-Key")) -> None:
    """Raise 403 if ADMIN_API_KEY is set and request does not provide it."""
    if not ADMIN_API_KEY:
        return
    if not x_admin_key or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup; start bot subprocess if active Telegram settings exist."""
    init_db()
    if get_telegram_settings_decrypted():
        start_bot()
    yield
    stop_bot()


app = FastAPI(title="LO_TG_BOT Admin API", lifespan=lifespan)

_admin_dir = Path(__file__).resolve().parent.parent / "admin"
if _admin_dir.exists():
    app.mount("/admin", StaticFiles(directory=str(_admin_dir), html=True), name="admin")


@app.get("/api/settings")
def get_settings(_: None = Depends(_require_admin)):
    """Return all settings (Telegram and LLM). Secrets are masked (last 5 chars)."""
    return {
        "telegram": get_telegram_settings(),
        "llm": get_llm_settings(),
    }


@app.post("/api/settings/telegram/test")
async def telegram_test(_: None = Depends(_require_admin)):
    """Test Telegram Bot API connection (getMe). Uses saved settings from DB. Async to avoid blocking."""
    status, message = await test_telegram_connection_async()
    return {"status": status, "message": message}


@app.put("/api/settings/telegram")
def put_telegram_settings(body: dict, _: None = Depends(_require_admin)):
    """
    Save Telegram block. Validate (accessToken required unless existing token).
    Task 5: if accessToken empty but we have saved token, keep it and only update base_url.
    Save, run test. If test fails, deactivate and stop bot (Task 3).
    """
    access_token = (body.get("accessToken") or "").strip() or None
    base_url = (body.get("baseUrl") or "").strip() or None
    if not access_token:
        creds = get_telegram_credentials_for_test()
        if creds and (creds.get("access_token") or "").strip():
            access_token = (creds["access_token"] or "").strip()
        if not access_token:
            raise HTTPException(status_code=400, detail="Access Token is required")
    try:
        save_telegram_settings(
            access_token=access_token,
            base_url=base_url,
            connection_status="not_configured",
            is_active=False,
        )
    except ValueError as e:
        if "SETTINGS_ENCRYPTION_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail="SETTINGS_ENCRYPTION_KEY is not set. Add it to .env and restart the app.",
            ) from e
        raise
    status, _message = test_telegram_connection()
    applied = status == CONNECTION_STATUS_SUCCESS
    if applied:
        set_telegram_active(True)
    else:
        set_telegram_active(False)
    restart_bot()
    settings = get_telegram_settings()
    return {"telegram": settings, "applied": applied}


@app.delete("/api/settings/telegram")
def delete_telegram_settings(_: None = Depends(_require_admin)):
    """Clear saved Telegram settings (token, base URL). Stops bot subprocess."""
    clear_telegram_settings()
    stop_bot()
    logger.info("settings_cleared block=telegram")
    return {"telegram": get_telegram_settings()}


@app.delete("/api/settings/telegram/token")
def delete_telegram_token(_: None = Depends(_require_admin)):
    """Unbind Telegram token (remove token, set is_active=False). Stops bot subprocess."""
    clear_telegram_token()
    stop_bot()
    logger.info("telegram_token_unbound")
    return {"telegram": get_telegram_settings()}


@app.post("/api/settings/telegram/activate")
def telegram_activate(_: None = Depends(_require_admin)):
    """Run connection test; if success, mark saved Telegram settings as active."""
    status, message = test_telegram_connection()
    activated = status == CONNECTION_STATUS_SUCCESS
    set_telegram_active(activated)
    if activated:
        restart_bot()
        logger.info("settings_activated block=telegram")
    return {"activated": activated, "message": message}


@app.post("/api/settings/llm/test")
async def llm_test(_: None = Depends(_require_admin)):
    """Test LLM provider connection. Uses saved settings from DB. Runs in thread to avoid blocking."""
    status, message = await asyncio.to_thread(test_llm_connection)
    return {"status": status, "message": message}


@app.patch("/api/settings/llm")
def patch_llm_settings(body: dict, _: None = Depends(_require_admin)):
    """
    Update only model_type, system_prompt, azure fields. No connection test; keeps is_active.
    Use when only model or system prompt changed (Task 4, 6).
    """
    model_type = (body.get("modelType") or "").strip()
    system_prompt = (body.get("systemPrompt") or "").strip() or None
    azure_endpoint = (body.get("azureEndpoint") or "").strip() or None
    api_version = (body.get("apiVersion") or "").strip() or None
    if not model_type:
        raise HTTPException(status_code=400, detail="Model type is required")
    updated = update_llm_model_and_prompt(
        model_type=model_type,
        system_prompt=system_prompt,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
    )
    if not updated:
        raise HTTPException(status_code=400, detail="No LLM settings to update (save provider and API key first)")
    logger.info("settings_updated block=llm fields_only model=%s", model_type)
    return {"llm": get_llm_settings(), "applied": True}


@app.put("/api/settings/llm")
def put_llm_settings(body: dict, _: None = Depends(_require_admin)):
    """
    Save LLM block. Validate llmType, apiKey (optional for ollama), modelType.
    If apiKey empty but active LLM exists, keep existing key. Base URL default from provider if empty.
    Save, run test, set active if success.
    """
    llm_type = (body.get("llmType") or "").strip()
    api_key = (body.get("apiKey") or "").strip() or None
    base_url = (body.get("baseUrl") or "").strip()
    model_type = (body.get("modelType") or "").strip()
    system_prompt = (body.get("systemPrompt") or "").strip() or None
    azure_endpoint = (body.get("azureEndpoint") or "").strip() or None
    api_version = (body.get("apiVersion") or "").strip() or None
    if not llm_type:
        raise HTTPException(status_code=400, detail="LLM type is required")
    if not model_type:
        raise HTTPException(status_code=400, detail="Model type is required")
    # Task 5: empty apiKey with existing active token → keep existing key
    if not api_key and llm_type.lower() != "ollama":
        creds = get_llm_credentials_for_test()
        if creds and creds.get("llm_type") == llm_type and (creds.get("api_key") or "").strip():
            api_key = (creds.get("api_key") or "").strip() or None
        if not api_key:
            raise HTTPException(status_code=400, detail="API key is required")
    if not base_url:
        base_url = get_default_base_url(llm_type) or ""
    try:
        save_llm_settings(
            llm_type=llm_type,
            api_key=api_key,
            base_url=base_url,
            model_type=model_type,
            system_prompt=system_prompt,
            connection_status="not_configured",
            is_active=False,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
        )
    except ValueError as e:
        if "SETTINGS_ENCRYPTION_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail="SETTINGS_ENCRYPTION_KEY is not set. Add it to .env and restart the app.",
            ) from e
        raise
    status, _message = test_llm_connection()
    applied = status == CONNECTION_STATUS_SUCCESS
    set_llm_active(applied)
    logger.info("settings_changed block=llm action=put applied=%s", applied)
    settings = get_llm_settings()
    return {"llm": settings, "applied": applied}


@app.delete("/api/settings/llm")
def delete_llm_settings(_: None = Depends(_require_admin)):
    """Clear saved LLM settings (provider, API key, model, etc.)."""
    clear_llm_settings()
    logger.info("settings_cleared block=llm")
    return {"llm": get_llm_settings()}


@app.delete("/api/settings/llm/token")
def delete_llm_token(_: None = Depends(_require_admin)):
    """Unbind LLM API key (remove key, set is_active=False). Keeps provider, base_url, model, system_prompt."""
    clear_llm_token()
    logger.info("llm_token_unbound")
    return {"llm": get_llm_settings()}


@app.post("/api/settings/llm/activate")
def llm_activate(_: None = Depends(_require_admin)):
    """Run connection test; if success, mark saved LLM settings as active."""
    status, message = test_llm_connection()
    activated = status == CONNECTION_STATUS_SUCCESS
    set_llm_active(activated)
    if activated:
        logger.info("settings_activated block=llm")
    return {"activated": activated, "message": message}


@app.get("/api/settings/llm/providers")
def get_llm_providers():
    """Return list of LLM providers with default base URLs and model lists (standard + reasoning)."""
    return {"providers": PROVIDERS_LIST}


@app.post("/api/settings/llm/fetch-models")
def fetch_llm_models(body: dict, _: None = Depends(_require_admin)):
    """
    Fetch model list from provider API (OpenAI-compatible GET /models or Anthropic GET /v1/models).
    Body: optional baseUrl, apiKey. If omitted, use saved LLM settings.
    Returns { "models": [ {"id": "...", "display_name": "..."? }, ... ], "error": null } or error in "error".
    """
    base_url = (body.get("baseUrl") or "").strip() or None
    api_key = (body.get("apiKey") or "").strip() or None
    creds = get_llm_credentials_for_test()
    if creds and (not base_url or not api_key):
        base_url = base_url or (creds.get("base_url") or "").strip()
        api_key = api_key or (creds.get("api_key") or "").strip()
    llm_type = (creds.get("llm_type") or "").strip().lower() if creds else ""
    if llm_type == "anthropic":
        if not api_key:
            return {"models": [], "error": "API key is required"}
        models, err = fetch_models_anthropic(api_key or "")
    elif llm_type == "google":
        if not api_key:
            return {"models": [], "error": "API key is required"}
        models, err = fetch_models_google(api_key or "")
    else:
        if not base_url:
            return {"models": [], "error": "Base URL is required"}
        models, err = fetch_models_from_api(base_url, api_key or "")
    if err:
        return {"models": [], "error": err}
    # OpenAI API часто возвращает только модели по доступу ключа. Всегда дополняем известными id (o1, o3, gpt-5 и др.).
    if (llm_type or "").strip().lower() == "openai":
        existing = {m["id"] for m in models}
        for mid in OPENAI_KNOWN_MODEL_IDS:
            if mid not in existing:
                models.append({"id": mid, "display_name": None})
                existing.add(mid)
    return {"models": models, "error": None}
