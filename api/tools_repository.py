"""CRUD for tool_settings. Encrypts/decrypts settings_json."""
import json
import logging
from typing import Any, Dict, List, Optional

from api.db import SessionLocal, ToolSettingsModel
from api.encryption import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


def _encrypt_settings(settings: dict) -> Optional[str]:
    if not settings:
        return None
    try:
        json_str = json.dumps(settings, ensure_ascii=False)
        return encrypt_secret(json_str)
    except Exception as e:
        logger.warning("Encrypt settings failed: %s", e)
        return None


def _decrypt_settings(encrypted: Optional[str]) -> dict:
    if not encrypted or not encrypted.strip():
        return {}
    json_str = decrypt_secret(encrypted)
    if not json_str:
        return {}
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}


def _mask_value(value: str) -> str:
    if not value or len(value) <= 5:
        return "***"
    return f"***{value[-5:]}"


def mask_settings(settings: dict, schema: Optional[List[Any]] = None) -> dict:
    """Mask password-type fields for API. schema is list of PluginSettingDefinition-like dicts."""
    if not schema:
        return dict(settings)
    out = dict(settings)
    for s in schema:
        key = s.get("key") if isinstance(s, dict) else getattr(s, "key", None)
        typ = s.get("type") if isinstance(s, dict) else getattr(s, "type", None)
        if key and typ == "password" and key in out and out[key]:
            out[key] = _mask_value(str(out[key]))
    return out


def get_tool_settings(tool_name: str) -> Optional[ToolSettingsModel]:
    """Get tool settings by name. Decrypts settings into record for callers."""
    with SessionLocal() as session:
        row = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.tool_name == tool_name
        ).first()
        if not row:
            return None
        # Attach decrypted settings for callers
        row._decrypted_settings = _decrypt_settings(row.settings_json)
        return row


def get_all_tool_settings() -> List[ToolSettingsModel]:
    """Get all tool settings with decrypted settings attached."""
    with SessionLocal() as session:
        rows = session.query(ToolSettingsModel).all()
        for row in rows:
            row._decrypted_settings = _decrypt_settings(row.settings_json)
        return list(rows)


def get_tool_settings_by_plugin(plugin_id: str) -> List[ToolSettingsModel]:
    """Get settings for tools of a specific plugin."""
    with SessionLocal() as session:
        rows = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.plugin_id == plugin_id
        ).all()
        for row in rows:
            row._decrypted_settings = _decrypt_settings(row.settings_json)
        return list(rows)


def save_tool_settings(
    tool_name: str,
    plugin_id: str,
    enabled: bool = False,
    settings: Optional[dict] = None,
) -> ToolSettingsModel:
    """Create or update tool settings. Settings dict is encrypted."""
    enc = _encrypt_settings(settings or {})
    with SessionLocal() as session:
        row = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.tool_name == tool_name
        ).first()
        if row:
            row.plugin_id = plugin_id
            row.enabled = enabled
            row.settings_json = enc
            session.commit()
            session.refresh(row)
            row._decrypted_settings = settings or {}
            return row
        row = ToolSettingsModel(
            tool_name=tool_name,
            plugin_id=plugin_id,
            enabled=enabled,
            settings_json=enc,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        row._decrypted_settings = settings or {}
        return row


def update_tool_enabled(tool_name: str, enabled: bool) -> bool:
    """Update only enabled status. Returns True if found."""
    with SessionLocal() as session:
        row = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.tool_name == tool_name
        ).first()
        if not row:
            return False
        row.enabled = enabled
        session.commit()
        return True


def update_tool_settings(tool_name: str, settings: dict) -> bool:
    """Update only settings (encrypted). Returns True if found."""
    enc = _encrypt_settings(settings)
    with SessionLocal() as session:
        row = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.tool_name == tool_name
        ).first()
        if not row:
            return False
        row.settings_json = enc
        session.commit()
        return True


def delete_tool_settings(tool_name: str) -> bool:
    """Delete tool settings. Returns True if deleted."""
    with SessionLocal() as session:
        row = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.tool_name == tool_name
        ).first()
        if not row:
            return False
        session.delete(row)
        session.commit()
        return True


def delete_plugin_settings(plugin_id: str) -> int:
    """Delete settings for all tools of a plugin. Returns count deleted."""
    with SessionLocal() as session:
        n = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.plugin_id == plugin_id
        ).delete()
        session.commit()
        return n
