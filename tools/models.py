"""
Data models for plugin system: tools, plugins, tool calls and results.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


# ---- Dataclasses (used in execution flow) ----

@dataclass
class ToolCall:
    """Tool call from LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Tool execution result."""
    tool_call_id: str
    content: str
    success: bool = True
    error: Optional[str] = None


# ---- Pydantic models (validation) ----

class ToolParameter(BaseModel):
    """Tool parameter description."""
    name: str
    type: str  # string, number, boolean, array, object
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None


class ToolManifestItem(BaseModel):
    """Tool description in plugin manifest."""
    name: str
    description: str
    handler: str
    timeout: int = 30
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PluginSettingDefinition(BaseModel):
    """Plugin setting description."""
    key: str
    label: str
    type: str  # string, password, number, boolean, select
    description: Optional[str] = None
    required: bool = False
    default: Any = None
    options: Optional[List[Any]] = None


class PluginManifest(BaseModel):
    """Plugin manifest (from plugin.yaml)."""
    id: str
    name: str
    version: str
    description: Optional[str] = None
    enabled: bool = True
    tools: List[ToolManifestItem]
    settings: List[PluginSettingDefinition] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    """Full tool description with bound handler."""
    name: str
    description: str
    plugin_id: str
    handler: Optional[Any] = None  # Callable, not serialized
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30
    enabled: bool = True

    class Config:
        arbitrary_types_allowed = True
