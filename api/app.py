"""FastAPI application for admin settings API."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

from api.db import CONNECTION_STATUS_SUCCESS, init_db
from api.llm_providers import (
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
from api.service_admins_repository import (
    ServiceAdminCreate,
    ServiceAdminList,
    ServiceAdminResponse,
    create_service_admin,
    delete_service_admin,
    get_all_service_admins,
    get_service_admin_by_telegram_id,
    refresh_service_admin_profile,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB; load plugins and sync settings; start bot subprocess if active Telegram settings exist."""
    init_db()
    try:
        from tools import load_all_plugins
        from tools.settings_manager import sync_settings_with_registry
        result = await load_all_plugins()
        logger.info("Loaded %d plugins with %d tools", len(result.loaded), result.total_tools)
        for e in result.failed:
            logger.error("Plugin load failed %s: %s", e.plugin_path, e.error)
        await sync_settings_with_registry()
        logger.info("Plugin settings synced with database")
    except Exception as e:
        logger.exception("Plugin loading failed: %s", e)
    if get_telegram_settings_decrypted():
        start_bot()
    yield
    stop_bot()


app = FastAPI(title="LO_TG_BOT Admin API", lifespan=lifespan)

_admin_dir = Path(__file__).resolve().parent.parent / "admin"
if _admin_dir.exists():
    app.mount("/admin", StaticFiles(directory=str(_admin_dir), html=True), name="admin")

from api.tools_router import router as tools_router
from api.plugins_router import router as plugins_router
from api.hr_router import router as hr_router
app.include_router(tools_router)
app.include_router(plugins_router)
app.include_router(hr_router)


@app.get("/api/settings")
def get_settings():
    """Return all settings (Telegram and LLM). Secrets are masked (last 5 chars)."""
    return {
        "telegram": get_telegram_settings(),
        "llm": get_llm_settings(),
    }


@app.post("/api/settings/telegram/test")
async def telegram_test():
    """Test Telegram Bot API connection (getMe). Uses saved settings from DB. Async to avoid blocking."""
    status, message = await test_telegram_connection_async()
    return {"status": status, "message": message}


@app.put("/api/settings/telegram")
async def put_telegram_settings(body: dict):
    """
    Save Telegram block. Validate (accessToken required unless existing token).
    Task 5: if accessToken empty but we have saved token, keep it and only update base_url.
    Save, run test in thread to avoid blocking event loop. If test fails, deactivate and stop bot (Task 3).
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
    status, _message = await asyncio.to_thread(test_telegram_connection)
    applied = status == CONNECTION_STATUS_SUCCESS
    if applied:
        set_telegram_active(True)
    else:
        set_telegram_active(False)
    restart_bot()
    settings = get_telegram_settings()
    return {"telegram": settings, "applied": applied}


@app.delete("/api/settings/telegram")
def delete_telegram_settings():
    """Clear saved Telegram settings (token, base URL). Stops bot subprocess."""
    clear_telegram_settings()
    stop_bot()
    logger.info("settings_cleared block=telegram")
    return {"telegram": get_telegram_settings()}


@app.delete("/api/settings/telegram/token")
def delete_telegram_token():
    """Unbind Telegram token (remove token, set is_active=False). Stops bot subprocess."""
    clear_telegram_token()
    stop_bot()
    logger.info("telegram_token_unbound")
    return {"telegram": get_telegram_settings()}


@app.post("/api/settings/telegram/activate")
async def telegram_activate():
    """Run connection test in thread; if success, mark saved Telegram settings as active."""
    status, message = await asyncio.to_thread(test_telegram_connection)
    activated = status == CONNECTION_STATUS_SUCCESS
    set_telegram_active(activated)
    if activated:
        restart_bot()
        logger.info("settings_activated block=telegram")
    return {"activated": activated, "message": message}


@app.post("/api/settings/llm/test")
async def llm_test():
    """Test LLM provider connection. Uses saved settings from DB. Runs in thread to avoid blocking."""
    status, message = await asyncio.to_thread(test_llm_connection)
    return {"status": status, "message": message}


@app.patch("/api/settings/llm")
async def patch_llm_settings(body: dict):
    """
    Update only model_type, system_prompt, azure fields, project_id. No connection test; keeps is_active.
    Use when only model or system prompt changed (Task 4, 6).
    """
    model_type = (body.get("modelType") or "").strip()
    system_prompt = (body.get("systemPrompt") or "").strip() or None
    azure_endpoint = (body.get("azureEndpoint") or "").strip() or None
    api_version = (body.get("apiVersion") or "").strip() or None
    # Check if projectId key exists in body to distinguish between "not provided" and "set to null"
    project_id = None
    if "projectId" in body:
        project_id = (body.get("projectId") or "").strip() or None
    if not model_type:
        raise HTTPException(status_code=400, detail="Model type is required")
    updated = update_llm_model_and_prompt(
        model_type=model_type,
        system_prompt=system_prompt,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        project_id=project_id,
        project_id_provided="projectId" in body,
    )
    if not updated:
        raise HTTPException(status_code=400, detail="No LLM settings to update (save provider and API key first)")
    logger.info("settings_updated block=llm fields_only model=%s", model_type)
    return {"llm": get_llm_settings(), "applied": True}


@app.put("/api/settings/llm")
async def put_llm_settings(body: dict):
    """
    Save LLM block. Validate llmType, apiKey (optional for ollama), modelType.
    If apiKey empty but active LLM exists, keep existing key. Base URL default from provider if empty.
    Save, run test in thread to avoid blocking, set active if success.
    """
    llm_type = (body.get("llmType") or "").strip()
    api_key = (body.get("apiKey") or "").strip() or None
    base_url = (body.get("baseUrl") or "").strip()
    model_type = (body.get("modelType") or "").strip()
    system_prompt = (body.get("systemPrompt") or "").strip() or None
    azure_endpoint = (body.get("azureEndpoint") or "").strip() or None
    api_version = (body.get("apiVersion") or "").strip() or None
    project_id = (body.get("projectId") or "").strip() or None
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
            project_id=project_id,
        )
    except ValueError as e:
        if "SETTINGS_ENCRYPTION_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail="SETTINGS_ENCRYPTION_KEY is not set. Add it to .env and restart the app.",
            ) from e
        raise
    status, _message = await asyncio.to_thread(test_llm_connection)
    applied = status == CONNECTION_STATUS_SUCCESS
    set_llm_active(applied)
    logger.info("settings_changed block=llm action=put applied=%s", applied)
    settings = get_llm_settings()
    return {"llm": settings, "applied": applied}


@app.delete("/api/settings/llm")
def delete_llm_settings():
    """Clear saved LLM settings (provider, API key, model, etc.)."""
    clear_llm_settings()
    logger.info("settings_cleared block=llm")
    return {"llm": get_llm_settings()}


@app.delete("/api/settings/llm/token")
def delete_llm_token():
    """Unbind LLM API key (remove key, set is_active=False). Keeps provider, base_url, model, system_prompt."""
    clear_llm_token()
    logger.info("llm_token_unbound")
    return {"llm": get_llm_settings()}


@app.post("/api/settings/llm/activate")
async def llm_activate():
    """Run connection test in thread; if success, mark saved LLM settings as active."""
    status, message = await asyncio.to_thread(test_llm_connection)
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
def fetch_llm_models(body: dict):
    """
    Fetch model list from provider API (OpenAI-compatible GET /models or Anthropic GET /v1/models).
    Body: optional baseUrl, apiKey, llmType, projectId. If omitted, use saved LLM settings.
    Returns { "models": [ {"id": "...", "display_name": "..."? }, ... ], "error": null } or error in "error".
    """
    base_url = (body.get("baseUrl") or "").strip() or None
    api_key = (body.get("apiKey") or "").strip() or None
    llm_type_from_body = (body.get("llmType") or "").strip().lower() or None
    project_id = (body.get("projectId") or "").strip() or None
    
    # Get saved credentials if not provided in body
    creds = get_llm_credentials_for_test()
    if creds and (not base_url or not api_key):
        base_url = base_url or (creds.get("base_url") or "").strip()
        api_key = api_key or (creds.get("api_key") or "").strip()
    if not project_id and creds:
        project_id = project_id or (creds.get("project_id") or "").strip() or None
    
    # Determine provider type: from body, from saved creds, or detect from base_url
    llm_type = llm_type_from_body
    if not llm_type and creds:
        llm_type = (creds.get("llm_type") or "").strip().lower()
    
    # Auto-detect provider from base_url if type not known
    if not llm_type and base_url:
        base_lower = base_url.lower()
        if "anthropic.com" in base_lower:
            llm_type = "anthropic"
        elif "generativelanguage.googleapis.com" in base_lower or "googleapis.com" in base_lower:
            llm_type = "google"
        elif "api.openai.com" in base_lower:
            llm_type = "openai"
        elif "groq.com" in base_lower:
            llm_type = "groq"
        elif "openrouter.ai" in base_lower:
            llm_type = "openrouter"
        elif "deepseek.com" in base_lower:
            llm_type = "deepseek"
        elif "x.ai" in base_lower:
            llm_type = "xai"
        elif "perplexity.ai" in base_lower:
            llm_type = "perplexity"
        elif "azure.com" in base_lower or "azureopenai" in base_lower:
            llm_type = "azure"
        elif "yandex" in base_lower:
            llm_type = "yandex"
        elif "localhost:11434" in base_lower or "ollama" in base_lower:
            llm_type = "ollama"
    
    # Route to appropriate fetch function
    if llm_type == "anthropic":
        if not api_key:
            return {"models": [], "error": "API key is required for Anthropic"}
        models, err = fetch_models_anthropic(api_key or "", project_id=project_id)
    elif llm_type == "google":
        if not api_key:
            return {"models": [], "error": "API key is required for Google"}
        models, err = fetch_models_google(api_key or "", project_id=project_id)
    else:
        # OpenAI-compatible providers (openai, groq, openrouter, ollama, etc.)
        # For OpenAI API, project_id is supported via OpenAI-Project header
        # For other providers, project_id is ignored
        if not base_url:
            return {"models": [], "error": "Base URL is required"}
        models, err = fetch_models_from_api(base_url, api_key or "", project_id=project_id)
    
    if err:
        return {"models": [], "error": err}
    
    # Return all models from provider
    return {"models": models, "error": None}


# --- Service admins ---


@app.get("/api/service-admins", response_model=ServiceAdminList)
async def list_service_admins():
    """Return all service admins."""
    admins = await asyncio.to_thread(get_all_service_admins)
    return ServiceAdminList(admins=admins, total=len(admins))


@app.post(
    "/api/service-admins",
    response_model=ServiceAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_service_admin(body: ServiceAdminCreate):
    """Add a service admin by Telegram ID. Fetches profile from Telegram in thread to avoid blocking."""
    try:
        admin, warning = await asyncio.to_thread(create_service_admin, body.telegram_id)
    except ValueError as e:
        msg = str(e)
        if "already a service admin" in msg:
            raise HTTPException(status_code=409, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    if warning:
        logger.info("service_admin_created telegram_id=%s warning=%s", body.telegram_id, warning)
    return admin


@app.get("/api/service-admins/{telegram_id}", response_model=ServiceAdminResponse)
async def get_service_admin(telegram_id: int):
    """Return one service admin by Telegram ID."""
    admin = await asyncio.to_thread(get_service_admin_by_telegram_id, telegram_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Service admin not found")
    return admin


@app.delete("/api/service-admins/{telegram_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_service_admin(telegram_id: int):
    """Remove a service admin."""
    deleted = await asyncio.to_thread(delete_service_admin, telegram_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Service admin not found")


@app.post("/api/service-admins/{telegram_id}/refresh", response_model=ServiceAdminResponse)
async def refresh_service_admin(telegram_id: int):
    """Refresh service admin profile from Telegram (runs in thread to avoid blocking)."""
    admin = await asyncio.to_thread(refresh_service_admin_profile, telegram_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Service admin not found")
    return admin
