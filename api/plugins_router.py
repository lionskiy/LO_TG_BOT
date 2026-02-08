"""REST API for plugins: list, reload."""
import logging

from fastapi import APIRouter, HTTPException

from api.tools_repository import get_all_tool_settings
from tools import get_registry, reload_plugin, reload_all_plugins
from tools.settings_manager import sync_settings_with_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("")
async def list_plugins():
    """List all plugins with tool counts."""
    reg = get_registry()
    db_records = get_all_tool_settings()
    enabled_by_tool = {r.tool_name: r.enabled for r in db_records}
    seen_plugins = {}
    for tool in reg.get_all_tools():
        pid = tool.plugin_id
        if pid not in seen_plugins:
            manifest = reg.get_plugin(pid)
            tools_of_plugin = reg.get_tools_by_plugin(pid)
            enabled_count = sum(
                1 for t in tools_of_plugin
                if enabled_by_tool.get(t.name, t.enabled)
            )
            seen_plugins[pid] = {
                "id": pid,
                "name": manifest.name if manifest else pid,
                "version": manifest.version if manifest else "",
                "description": (manifest.description or "") if manifest else "",
                "tools_count": len(tools_of_plugin),
                "enabled_count": enabled_count,
            }
    plugins = list(seen_plugins.values())
    return {"plugins": plugins, "total": len(plugins)}


@router.post("/reload")
async def reload_all():
    """Reload all plugins and sync settings from DB."""
    result = await reload_all_plugins()
    await sync_settings_with_registry()
    return {
        "success": True,
        "message": "Plugins reloaded",
        "loaded": result.loaded,
        "failed": [{"plugin_path": e.plugin_path, "error": e.error} for e in result.failed],
        "total_tools": result.total_tools,
    }


@router.post("/{plugin_id}/reload")
async def reload_one(plugin_id: str):
    """Reload one plugin by id."""
    ok = await reload_plugin(plugin_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    await sync_settings_with_registry()
    reg = get_registry()
    tools = reg.get_tools_by_plugin(plugin_id)
    return {"success": True, "message": f"Plugin '{plugin_id}' reloaded", "tools_count": len(tools)}
