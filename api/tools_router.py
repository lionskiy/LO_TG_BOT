"""REST API for tools: list, get, enable/disable, settings."""
import logging
import os
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException

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
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()


def _require_admin(x_admin_key: str | None = Header(None, alias="X-Admin-Key")):
    if ADMIN_API_KEY and x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("")
async def list_tools(_: None = Depends(_require_admin)):
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
async def get_tool(name: str, _: None = Depends(_require_admin)):
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
async def enable_tool(name: str, _: None = Depends(_require_admin)):
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
async def disable_tool(name: str, _: None = Depends(_require_admin)):
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
async def get_tool_settings_endpoint(name: str, _: None = Depends(_require_admin)):
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
async def put_tool_settings(name: str, body: dict, _: None = Depends(_require_admin)):
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


@router.post("/{name}/test")
async def test_tool_connection(name: str, _: None = Depends(_require_admin)):
    """Test tool connection. Most tools do not support this."""
    reg = get_registry()
    if not reg.get_tool(name):
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    return {"success": False, "message": f"Tool '{name}' does not support connection testing"}
