"""
Tool registry: centralized store of registered tools and plugins.
Singleton per application.
"""
import logging
from typing import Any, Dict, List, Optional

from tools.models import PluginManifest, ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Tool registry. Singleton — one instance per application.
    """
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self._plugins: Dict[str, PluginManifest] = {}

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool. Raises ValueError if name already exists."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool
        logger.debug("Registered tool %s (plugin=%s)", tool.name, tool.plugin_id)

    def register_plugin(self, manifest: PluginManifest) -> None:
        """Register a plugin (without tools). Tools are registered separately."""
        self._plugins[manifest.id] = manifest
        logger.debug("Registered plugin %s", manifest.id)

    def unregister_plugin(self, plugin_id: str) -> None:
        """Remove plugin and all its tools. Used on hot-reload."""
        to_remove = [name for name, t in self._tools.items() if t.plugin_id == plugin_id]
        for name in to_remove:
            del self._tools[name]
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
        logger.debug("Unregistered plugin %s (removed %d tools)", plugin_id, len(to_remove))

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name."""
        return self._tools.get(name)

    def get_plugin(self, plugin_id: str) -> Optional[PluginManifest]:
        """Get plugin manifest by id."""
        return self._plugins.get(plugin_id)

    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all tools (including disabled)."""
        return list(self._tools.values())

    def get_enabled_tools(self) -> List[ToolDefinition]:
        """Get only enabled tools."""
        return [t for t in self._tools.values() if t.enabled]

    def get_tools_by_plugin(self, plugin_id: str) -> List[ToolDefinition]:
        """Get tools of a specific plugin."""
        return [t for t in self._tools.values() if t.plugin_id == plugin_id]

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        Return list of tools in OpenAI format for LLM. Only enabled tools.
        """
        result = []
        for t in self._tools.values():
            if not t.enabled:
                continue
            result.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            })
        return result

    def enable_tool(self, name: str) -> bool:
        """Enable tool. Returns success."""
        if name not in self._tools:
            return False
        self._tools[name].enabled = True
        return True

    def disable_tool(self, name: str) -> bool:
        """Disable tool. Returns success."""
        if name not in self._tools:
            return False
        self._tools[name].enabled = False
        return True

    def is_tool_enabled(self, name: str) -> bool:
        """Check if tool is enabled."""
        t = self._tools.get(name)
        return t.enabled if t else False

    def clear(self) -> None:
        """Clear registry (for tests and reload)."""
        self._tools.clear()
        self._plugins.clear()
        logger.debug("Registry cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Registry statistics."""
        enabled = sum(1 for t in self._tools.values() if t.enabled)
        return {
            "total_plugins": len(self._plugins),
            "total_tools": len(self._tools),
            "enabled_tools": enabled,
        }


_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get global registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
