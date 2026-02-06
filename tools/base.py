"""
Plugin utilities: settings access, HTTP client, logging.
Phase 2: get_plugin_setting returns default (DB in Phase 3).
"""
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    """
    Get plugin setting value. Phase 2: returns default. Phase 3+: from DB.
    """
    # TODO Phase 3: read from DB
    return default


def require_plugin_setting(plugin_id: str, key: str) -> Any:
    """Get required setting. Raises PluginConfigError if not set."""
    value = get_plugin_setting(plugin_id, key)
    if value is None:
        raise ValueError(f"Plugin {plugin_id}: required setting '{key}' is not set")
    return value


def get_http_client(
    timeout: float = 30.0,
    follow_redirects: bool = True,
):
    """Get configured HTTP client (httpx.AsyncClient)."""
    import httpx
    return httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects)


def get_plugin_logger(plugin_id: str) -> logging.Logger:
    """Get logger for plugin with [plugin_id] prefix."""
    return logging.getLogger(f"plugin.{plugin_id}")


@dataclass
class ToolContext:
    """Tool execution context (for future use)."""
    user_id: Optional[str] = None
    chat_id: Optional[str] = None
    plugin_id: Optional[str] = None


_current_context: Optional[ToolContext] = None


def get_current_context() -> Optional[ToolContext]:
    """Get current execution context."""
    return _current_context
