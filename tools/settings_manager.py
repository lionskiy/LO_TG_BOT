"""
Plugin settings: read/write from DB, validation, sync with registry.
Phase 3: get_plugin_settings/save_plugin_settings use tools_repository.
"""
import logging
from typing import Any, List

from api.tools_repository import (
    get_tool_settings,
    get_all_tool_settings,
    save_tool_settings,
    mask_settings as _mask_settings,
)
from tools.models import PluginSettingDefinition

logger = logging.getLogger(__name__)


def get_plugin_settings(plugin_id: str) -> dict:
    """Get all plugin settings from DB (by first tool of plugin)."""
    from tools import get_registry
    registry = get_registry()
    tools = registry.get_tools_by_plugin(plugin_id)
    if not tools:
        return {}
    tool_name = tools[0].name
    record = get_tool_settings(tool_name)
    if record and getattr(record, "_decrypted_settings", None) is not None:
        return record._decrypted_settings
    return {}


def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    """Get a specific plugin setting."""
    settings = get_plugin_settings(plugin_id)
    return settings.get(key, default)


def save_plugin_settings(plugin_id: str, settings: dict, enabled: bool | None = None) -> None:
    """Save plugin settings for all plugin tools."""
    from tools import get_registry
    registry = get_registry()
    tools = registry.get_tools_by_plugin(plugin_id)
    for tool in tools:
        save_tool_settings(
            tool_name=tool.name,
            plugin_id=plugin_id,
            enabled=enabled if enabled is not None else tool.enabled,
            settings=settings,
        )


def is_plugin_configured(plugin_id: str) -> bool:
    """Check that all required settings are set."""
    from tools import get_registry
    registry = get_registry()
    manifest = registry.get_plugin(plugin_id)
    if not manifest or not getattr(manifest, "settings", None):
        return True
    settings = get_plugin_settings(plugin_id)
    for setting_def in manifest.settings:
        req = getattr(setting_def, "required", False)
        if req:
            value = settings.get(getattr(setting_def, "key", ""))
            if value is None or value == "":
                return False
    return True


def get_missing_settings(plugin_id: str) -> List[str]:
    """List of missing required setting keys."""
    from tools import get_registry
    registry = get_registry()
    manifest = registry.get_plugin(plugin_id)
    if not manifest or not getattr(manifest, "settings", None):
        return []
    settings = get_plugin_settings(plugin_id)
    missing = []
    for setting_def in manifest.settings:
        if getattr(setting_def, "required", False):
            key = getattr(setting_def, "key", "")
            value = settings.get(key)
            if value is None or value == "" or (isinstance(value, str) and value.startswith("***")):
                missing.append(key)
    return missing


def validate_plugin_settings(settings: dict, schema: List[Any]) -> List[dict]:
    """Validate settings against schema. Returns list of {field, error}."""
    errors = []
    for setting_def in schema:
        key = getattr(setting_def, "key", None) or (setting_def.get("key") if isinstance(setting_def, dict) else None)
        typ = getattr(setting_def, "type", None) or (setting_def.get("type") if isinstance(setting_def, dict) else None)
        req = getattr(setting_def, "required", False) or (setting_def.get("required", False) if isinstance(setting_def, dict) else False)
        value = settings.get(key) if key else None
        if req and (value is None or value == ""):
            if not (isinstance(value, str) and value and value.startswith("***")):
                errors.append({"field": key, "error": "Required field is empty"})
            continue
        if value is not None and value != "" and typ == "number":
            if not isinstance(value, (int, float)):
                try:
                    float(value)
                except (TypeError, ValueError):
                    errors.append({"field": key, "error": "Must be a number"})
        elif value is not None and value != "" and typ == "boolean":
            if not isinstance(value, bool):
                errors.append({"field": key, "error": "Must be true or false"})
    return errors


def mask_settings_for_api(settings: dict, schema: List[Any]) -> dict:
    """Mask secret fields for API response."""
    schema_list = []
    for s in schema:
        if isinstance(s, dict):
            schema_list.append(s)
        else:
            schema_list.append({"key": getattr(s, "key", None), "type": getattr(s, "type", None)})
    return _mask_settings(settings, schema_list)


async def sync_settings_with_registry() -> None:
    """Sync enabled status from DB to Registry. Call after loading plugins."""
    from tools import get_registry
    registry = get_registry()
    db_settings = get_all_tool_settings()
    for record in db_settings:
        tool = registry.get_tool(record.tool_name)
        if tool:
            if record.enabled:
                registry.enable_tool(record.tool_name)
            else:
                registry.disable_tool(record.tool_name)
    logger.debug("Synced %d tool settings to registry", len(db_settings))
