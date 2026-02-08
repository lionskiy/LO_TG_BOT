"""REST API for tools: list, get, enable/disable, settings."""
import logging
from typing import List

import httpx
from fastapi import APIRouter, HTTPException

from api.tools_repository import (
    get_tool_settings,
    get_all_tool_settings,
    save_tool_settings,
    update_tool_enabled,
)
from tools import get_registry
from tools.settings_manager import (
    get_plugin_settings,
    get_missing_settings,
    validate_plugin_settings,
    mask_settings_for_api,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
async def list_tools():
    """Get list of all tools with statuses."""
    reg = get_registry()
    db_records = {r.tool_name: r for r in get_all_tool_settings()}
    tools = []
    for t in reg.get_all_tools():
        rec = db_records.get(t.name)
        enabled = rec.enabled if rec else t.enabled
        manifest = reg.get_plugin(t.plugin_id)
        schema = getattr(manifest, "settings", None) or []
        missing = get_missing_settings(t.plugin_id) if schema else []
        plugin_name = manifest.name if manifest else t.plugin_id
        tools.append({
            "name": t.name,
            "description": t.description,
            "plugin_id": t.plugin_id,
            "plugin_name": plugin_name,
            "enabled": enabled,
            "needs_config": bool(missing),
            "has_settings": bool(schema),
        })
    enabled_count = sum(1 for r in db_records.values() if r.enabled) + sum(
        1 for t in reg.get_all_tools() if t.name not in db_records and t.enabled
    )
    return {"tools": tools, "total": len(tools), "enabled_count": enabled_count}


@router.get("/{name}")
async def get_tool(name: str):
    """Get full tool information."""
    reg = get_registry()
    tool = reg.get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    manifest = reg.get_plugin(tool.plugin_id)
    rec = get_tool_settings(name)
    enabled = rec.enabled if rec else tool.enabled
    schema = getattr(manifest, "settings", None) or []
    settings_dict = get_plugin_settings(tool.plugin_id)
    current_masked = mask_settings_for_api(settings_dict, schema) if schema else {}
    missing = get_missing_settings(tool.plugin_id) if schema else []
    schema_for_api = [
        {"key": s.key, "label": s.label, "type": s.type, "required": s.required, "description": s.description}
        for s in schema
    ]
    return {
        "name": tool.name,
        "description": tool.description,
        "plugin_id": tool.plugin_id,
        "plugin_name": manifest.name if manifest else tool.plugin_id,
        "plugin_version": manifest.version if manifest else "",
        "enabled": enabled,
        "needs_config": bool(missing),
        "parameters": tool.parameters,
        "settings_schema": schema_for_api,
        "current_settings": current_masked,
        "missing_settings": missing,
    }


@router.post("/{name}/enable")
async def enable_tool(name: str):
    """Enable tool. Returns 400 if required settings missing."""
    reg = get_registry()
    tool = reg.get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    missing = get_missing_settings(tool.plugin_id)
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": f"Tool '{name}' requires configuration", "missing_settings": missing},
        )
    reg.enable_tool(name)
    rec = get_tool_settings(name)
    if rec:
        update_tool_enabled(name, True)
    else:
        save_tool_settings(tool_name=name, plugin_id=tool.plugin_id, enabled=True, settings={})
    return {"success": True, "message": f"Tool '{name}' enabled"}


@router.post("/{name}/disable")
async def disable_tool(name: str):
    """Disable tool."""
    reg = get_registry()
    tool = reg.get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    reg.disable_tool(name)
    rec = get_tool_settings(name)
    if rec:
        update_tool_enabled(name, False)
    else:
        save_tool_settings(tool_name=name, plugin_id=tool.plugin_id, enabled=False, settings={})
    return {"success": True, "message": f"Tool '{name}' disabled"}


@router.get("/{name}/settings")
async def get_tool_settings_endpoint(name: str):
    """Get tool settings (masked)."""
    reg = get_registry()
    tool = reg.get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    manifest = reg.get_plugin(tool.plugin_id)
    schema = getattr(manifest, "settings", None) or []
    settings = get_plugin_settings(tool.plugin_id)
    masked = mask_settings_for_api(settings, schema)
    schema_api = [{"key": s.key, "label": s.label, "type": s.type, "required": s.required} for s in schema]
    return {"plugin_id": tool.plugin_id, "settings": masked, "schema": schema_api}


@router.put("/{name}/settings")
async def put_tool_settings(name: str, body: dict):
    """Save tool settings. Masked password values (***...) are preserved. Does not change enabled (per plan)."""
    reg = get_registry()
    tool = reg.get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    manifest = reg.get_plugin(tool.plugin_id)
    schema = getattr(manifest, "settings", None) or []
    new_settings = dict(body.get("settings") or body)
    current = get_plugin_settings(tool.plugin_id)
    for key, val in list(new_settings.items()):
        if isinstance(val, str) and val.startswith("***") and len(val) > 3 and key in current:
            new_settings[key] = current[key]
    errors = validate_plugin_settings(new_settings, schema)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": "Validation failed", "errors": errors},
        )
    rec = get_tool_settings(name)
    enabled = rec.enabled if rec else tool.enabled
    save_tool_settings(tool_name=name, plugin_id=tool.plugin_id, enabled=enabled, settings=new_settings)
    return {"success": True, "message": "Settings saved"}


async def _test_get_worklogs_connection() -> tuple[bool, str]:
    """Test Jira/Tempo connection using get_worklogs plugin settings. Returns (success, message)."""
    rec = get_tool_settings("get_worklogs")
    if not rec or not getattr(rec, "_decrypted_settings", None):
        return False, "Настройки инструмента get_worklogs не найдены. Сохраните настройки и повторите."
    s = rec._decrypted_settings
    base = (s.get("jira_url") or "").strip().rstrip("/")
    token = s.get("api_token") or ""
    if not base:
        return False, "Укажите Jira URL в настройках."
    if not token or token.startswith("***"):
        return False, "Укажите API Token в настройках (не маска)."
    url = f"{base}/rest/api/2/myself"
    try:
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            r = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
        if r.status_code == 200:
            return True, "Подключение к Jira успешно."
        if r.status_code == 401:
            return False, "Неверный API Token или нет доступа."
        return False, f"Jira вернул код {r.status_code}: {r.text[:200] if r.text else ''}"
    except httpx.RequestError as e:
        return False, f"Ошибка подключения: {e!s}"


@router.post("/{name}/test")
async def test_tool_connection(name: str):
    """Test tool connection. Supported for get_worklogs (Jira/Tempo)."""
    reg = get_registry()
    if not reg.get_tool(name):
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    if name == "get_worklogs":
        success, message = await _test_get_worklogs_connection()
        return {"success": success, "message": message}
    return {"success": False, "message": f"Tool '{name}' does not support connection testing"}
