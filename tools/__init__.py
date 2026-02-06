"""
Tools — plugin system for LO_TG_BOT.

Usage:
    from tools import get_registry, load_all_plugins, execute_tool

    await load_all_plugins()
    tools = get_registry().get_tools_for_llm()
    result = await execute_tool(tool_call)
"""
from tools.models import (
    PluginManifest,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from tools.registry import ToolRegistry, get_registry
from tools.loader import (
    load_all_plugins,
    load_plugin,
    reload_plugin,
    reload_all_plugins,
    LoadResult,
    LoadError,
)
from tools.executor import execute_tool, execute_tools
from tools.base import (
    get_plugin_setting,
    require_plugin_setting,
    get_http_client,
    get_plugin_logger,
)

__all__ = [
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "PluginManifest",
    "ToolRegistry",
    "get_registry",
    "load_all_plugins",
    "load_plugin",
    "reload_plugin",
    "reload_all_plugins",
    "LoadResult",
    "LoadError",
    "execute_tool",
    "execute_tools",
    "get_plugin_setting",
    "require_plugin_setting",
    "get_http_client",
    "get_plugin_logger",
]
