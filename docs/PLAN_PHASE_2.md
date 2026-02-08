# PHASE 2: Plugin System

> **Detailed task breakdown for Phase 2**  
> Plugin system: Registry, Loader, Executor, Builtin plugins

**Version:** 1.0  
**Date:** 2026-02-06  
**Estimated duration:** 5–7 days  
**Prerequisite:** Phase 1 done (tool-calling works)

---

## Related documents

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target system architecture | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Task breakdown | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Phase 0–1 detailed plan | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Phase 2 detailed plan (this document) | ✅ Current (in progress) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Phase 3 detailed plan (next) | ✅ Current (in progress) |

### Current implementation (v1.0)

| Document | Description |
|----------|-------------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Current implementation spec |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

---

## Phase navigation

| Phase | Document | Description | Status |
|------|----------|----------|--------|
| 0-1 | [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Stabilization + Tool-Calling | ✅ Current (in progress) |
| 2 | **[PLAN_PHASE_2.md](PLAN_PHASE_2.md)** | Plugin System | ✅ Current (in progress) |
| 3 | [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Storage + API | ✅ Current (in progress) |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Admin Tools | ✅ Current (in progress) |
| 5 | [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Admin Administrators | ✅ Current (in progress) |
| 6 | [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Worklog Checker | ✅ Current (in progress) |

---

## Phase 2 goal

**Before (after Phase 1):** Tool-calling works but tools are hardcoded in `bot/tool_calling.py`.

**After:** Tools are loaded from `plugins/` as separate modules. Adding a new tool = adding files to the folder (no core code changes).

**Important:** 
- Hardcoded tools from Phase 1 are moved to plugins
- Tool-calling keeps working unchanged for the user
- Plugin settings are NOT stored in DB yet (Phase 3)

---

## Phase 2 architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  telegram_bot.py                                                            │
│  │                                                                          │
│  └── handle_message() → get_reply_with_tools()                              │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │  tool_calling.py                                                        │
│  │                                                                         │
│  │  get_reply_with_tools(messages)                                         │
│  │  │                                                                      │
│  │  ├── tools = registry.get_tools_for_llm()    ← CHANGE               │
│  │  ├── response = llm.get_reply(messages, tools)                          │
│  │  ├── if tool_calls:                                                     │
│  │  │   └── result = executor.execute(tool_call)  ← CHANGE             │
│  │  └── return final_response                                              │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
│                              │
│              ┌───────────────┼───────────────┐
│              ▼               ▼               ▼
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  │   Registry    │  │   Executor    │  │    Loader     │
│  │               │  │               │  │               │
│  │ • tools dict  │  │ • execute()   │  │ • scan()      │
│  │ • get_tools() │  │ • timeout     │  │ • load()      │
│  │ • get_tool()  │  │ • errors      │  │ • reload()    │
│  └───────────────┘  └───────────────┘  └───────────────┘
│         ▲                                     │
│         │                                     │
│         └─────────────────────────────────────┘
│                       registration
│                              │
│                              ▼
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │  plugins/                                                               │
│  │  │                                                                      │
│  │  ├── builtin/                                                           │
│  │  │   ├── calculator/                                                    │
│  │  │   │   ├── plugin.yaml                                                │
│  │  │   │   └── handlers.py                                                │
│  │  │   │                                                                  │
│  │  │   └── datetime_tools/                                                │
│  │  │       ├── plugin.yaml                                                │
│  │  │       └── handlers.py                                                │
│  │  │                                                                      │
│  │  └── (future plugins...)                                               │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## tools/ folder structure

```
LO_TG_BOT/
├── tools/                      # Plugin system module
│   ├── __init__.py             # Public API export
│   ├── models.py               # Pydantic models (ToolDefinition, PluginManifest, etc.)
│   ├── registry.py             # Tool Registry
│   ├── loader.py               # Plugin Loader
│   ├── executor.py             # Tool Executor
│   └── base.py                 # Plugin utilities
│
└── plugins/                    # Plugins folder
    ├── __init__.py             # Empty
    └── builtin/                # Built-in plugins
        ├── calculator/
        │   ├── plugin.yaml
        │   └── handlers.py
        └── datetime_tools/
            ├── plugin.yaml
            └── handlers.py
```

---

# Phase 2

---

## Task 2.1: Data models (tools/models.py)

### Description
Create Pydantic models to describe plugins, tools and related structures.

### File: tools/models.py

### Models

#### ToolParameter
```python
class ToolParameter(BaseModel):
    """Tool parameter description"""
    name: str
    type: str                    # string, number, boolean, array, object
    description: str
    required: bool = False
    default: Any = None
    enum: List[Any] | None = None  # For limited set of values
```

#### ToolDefinition
```python
class ToolDefinition(BaseModel):
    """Full tool description"""
    name: str                    # Unique name (e.g.: "calculate")
    description: str             # Description for LLM (English)
    plugin_id: str               # Owner plugin ID
    handler: Callable | None = None  # Handler function (not serialized)
    parameters: Dict[str, Any]   # JSON Schema of parameters
    timeout: int = 30            # Execution timeout in seconds
    enabled: bool = True         # Whether tool is enabled
    
    class Config:
        arbitrary_types_allowed = True  # For Callable
```

#### PluginSettingDefinition
```python
class PluginSettingDefinition(BaseModel):
    """Plugin setting description"""
    key: str                     # Setting key
    label: str                   # Label for UI
    type: str                    # string, password, number, boolean, select
    description: str | None = None
    required: bool = False
    default: Any = None
    options: List[Any] | None = None  # For select
```

#### PluginManifest
```python
class PluginManifest(BaseModel):
    """Plugin manifest (from plugin.yaml)"""
    id: str                      # Unique plugin ID
    name: str                    # Label for UI
    version: str                 # Version (semver)
    description: str | None = None
    enabled: bool = True         # Enabled by default
    tools: List[ToolManifestItem]  # Tool list
    settings: List[PluginSettingDefinition] = []  # Plugin settings
```

#### ToolManifestItem
```python
class ToolManifestItem(BaseModel):
    """Tool description in manifest"""
    name: str
    description: str
    handler: str                 # Function name in handlers.py
    timeout: int = 30
    parameters: Dict[str, Any]   # JSON Schema
```

#### ToolCall and ToolResult (moved from Phase 1)
```python
@dataclass
class ToolCall:
    """Tool call from LLM"""
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass  
class ToolResult:
    """Tool execution result"""
    tool_call_id: str
    content: str
    success: bool = True
    error: str | None = None
```

### Done when
- [ ] All models created in tools/models.py
- [ ] Models validate data (Pydantic)
- [ ] ToolCall/ToolResult moved from bot/llm.py
- [ ] Model validation tests

---

## Task 2.2: Tool Registry (tools/registry.py)

### Description
Centralized store of all registered tools. Provides API for registration, retrieval and management of tools.

### File: tools/registry.py

### ToolRegistry class

```python
class ToolRegistry:
    """
    Tool registry.
    Singleton — one instance per application.
    """
```

### Internal storage
```python
_tools: Dict[str, ToolDefinition] = {}      # tool_name → ToolDefinition
_plugins: Dict[str, PluginManifest] = {}    # plugin_id → PluginManifest
```

### Public methods

#### Registration
```python
def register_tool(self, tool: ToolDefinition) -> None:
    """
    Registers a tool in the registry.
    
    Args:
        tool: Tool definition
        
    Raises:
        ValueError: If a tool with this name already exists
    """
    
def register_plugin(self, manifest: PluginManifest) -> None:
    """
    Registers a plugin (without tools).
    Tools are registered separately via register_tool().
    """

def unregister_plugin(self, plugin_id: str) -> None:
    """
    Removes plugin and all its tools from the registry.
    Used on hot-reload.
    """
```

#### Retrieving tools
```python
def get_tool(self, name: str) -> ToolDefinition | None:
    """Get tool by name"""

def get_all_tools(self) -> List[ToolDefinition]:
    """Get all tools (including disabled)"""

def get_enabled_tools(self) -> List[ToolDefinition]:
    """Get only enabled tools"""

def get_tools_by_plugin(self, plugin_id: str) -> List[ToolDefinition]:
    """Get tools of a specific plugin"""
```

#### Formatting for LLM
```python
def get_tools_for_llm(self) -> List[Dict[str, Any]]:
    """
    Returns list of tools in OpenAI format for passing to LLM.
    Only enabled tools.
    
    Returns:
        [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "...",
                    "parameters": {...}
                }
            },
            ...
        ]
    """
```

#### State management
```python
def enable_tool(self, name: str) -> bool:
    """Enable tool. Returns success."""

def disable_tool(self, name: str) -> bool:
    """Disable tool. Returns success."""

def is_tool_enabled(self, name: str) -> bool:
    """Check if tool is enabled"""
```

#### Internal
```python
def clear(self) -> None:
    """Clear registry (for tests and reload)"""

def get_stats(self) -> Dict[str, Any]:
    """
    Registry statistics.
    Returns: {
        "total_plugins": 2,
        "total_tools": 3,
        "enabled_tools": 2
    }
    """
```

### Singleton pattern
```python
# Global instance
_registry: ToolRegistry | None = None

def get_registry() -> ToolRegistry:
    """Get global registry instance"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
```

### Done when
- [ ] ToolRegistry class implemented
- [ ] All public methods work
- [ ] get_tools_for_llm() returns correct format
- [ ] Singleton works
- [ ] Tests for all methods

---

## Task 2.3: Plugin Loader (tools/loader.py)

### Description
Scans `plugins/` folder, reads manifests, loads handler code and registers tools in Registry.

### File: tools/loader.py

### Main functions

#### load_all_plugins
```python
async def load_all_plugins(
    plugins_dir: str = "plugins",
    registry: ToolRegistry | None = None
) -> LoadResult:
    """
    Loads all plugins from the given directory.
    
    Args:
        plugins_dir: Path to plugins folder
        registry: Registry (if None, global one is used)
        
    Returns:
        LoadResult with info on loaded plugins and errors
    """
```

#### load_plugin
```python
async def load_plugin(
    plugin_path: str,
    registry: ToolRegistry | None = None
) -> PluginManifest | None:
    """
    Loads one plugin from the given folder.
    
    Args:
        plugin_path: Path to plugin folder (contains plugin.yaml)
        registry: Registry to register with
        
    Returns:
        PluginManifest if success, None on error
        
    Raises:
        PluginLoadError: On critical load errors
    """
```

#### reload_plugin
```python
async def reload_plugin(
    plugin_id: str,
    plugins_dir: str = "plugins",
    registry: ToolRegistry | None = None
) -> bool:
    """
    Reloads plugin (unregister + load).
    
    Steps:
    1. Find plugin folder by ID
    2. Remove from registry (unregister_plugin)
    3. Reload Python module (importlib.reload)
    4. Load again (load_plugin)
    
    Returns:
        True if successful
    """
```

#### reload_all_plugins
```python
async def reload_all_plugins(
    plugins_dir: str = "plugins",
    registry: ToolRegistry | None = None
) -> LoadResult:
    """
    Reloads all plugins.
    
    Steps:
    1. Clear registry
    2. Load all plugins again
    """
```

### Structure LoadResult
```python
@dataclass
class LoadResult:
    """Plugin load result"""
    loaded: List[str]            # IDs of successfully loaded plugins
    failed: List[LoadError]      # Load errors
    total_tools: int             # Total tools loaded

@dataclass
class LoadError:
    """Plugin load error"""
    plugin_id: str | None        # Plugin ID (if known)
    plugin_path: str             # Path to folder
    error: str                   # Error message
    exception: Exception | None  # Exception (for logs)
```

### Plugin load algorithm

```
load_plugin(plugin_path):
│
├── 1. READ MANIFEST
│   ├── Check plugin.yaml exists
│   ├── Read YAML
│   ├── Validate via PluginManifest (Pydantic)
│   └── On error → return None, log
│
├── 2. LOAD CODE
│   ├── Check handlers.py exists
│   ├── Load module via importlib.util
│   │   ├── spec = importlib.util.spec_from_file_location(...)
│   │   ├── module = importlib.util.module_from_spec(spec)
│   │   └── spec.loader.exec_module(module)
│   └── On error → return None, log
│
├── 3. BINDING HANDLERS
│   ├── For each tool in manifest.tools:
│   │   ├── Find handler function in module
│   │   ├── Check it is callable
│   │   ├── Check async (optional)
│   │   └── On error → skip tool, log
│   │
│   └── Create ToolDefinition with bound handler
│
├── 4. REGISTRATION
│   ├── registry.register_plugin(manifest)
│   └── For each tool:
│       └── registry.register_tool(tool_definition)
│
└── 5. RESULT
    ├── Log success
    └── Return manifest
```

### Error handling

| Situation | Behaviour |
|----------|-----------|
| plugin.yaml not found | Skip folder, warning to log |
| plugin.yaml invalid | Skip plugin, error to log |
| handlers.py not found | Skip plugin, error to log |
| handlers.py import error | Skip plugin, error to log |
| Handler function not found | Skip tool, warning to log |
| Handler not callable | Skip tool, warning to log |

### Filtering when scanning
```python
IGNORE_DIRS = {'__pycache__', '.git', '.idea', 'node_modules', '.venv'}

def _should_scan_dir(dirname: str) -> bool:
    """Checks whether to scan folder"""
    return (
        not dirname.startswith('.') and
        not dirname.startswith('_') and
        dirname not in IGNORE_DIRS
    )
```

### Done when
- [ ] load_all_plugins() loads plugins from folder
- [ ] load_plugin() loads one plugin
- [ ] reload_plugin() reloads plugin
- [ ] Manifest validated via Pydantic
- [ ] Handlers loaded via importlib
- [ ] Errors do not break loading other plugins
- [ ] Logging all stages
- [ ] Tests for successful load
- [ ] Tests for errors (bad YAML, missing handler)

---

## Task 2.4: Tool Executor (tools/executor.py)

### Description
Executes tools: gets ToolCall, finds handler in Registry, calls with arguments, returns result.

### File: tools/executor.py

### Main function

```python
async def execute_tool(
    tool_call: ToolCall,
    registry: ToolRegistry | None = None,
    timeout: int | None = None
) -> ToolResult:
    """
    Executes a tool call.
    
    Args:
        tool_call: Call from LLM (name, arguments)
        registry: Tool registry
        timeout: Timeout (if None — from ToolDefinition)
        
    Returns:
        ToolResult with result or error
    """
```

### Execution algorithm

```
execute_tool(tool_call):
│
├── 1. FIND TOOL
│   ├── tool = registry.get_tool(tool_call.name)
│   ├── If not found → return ToolResult with error
│   └── If disabled → return ToolResult with error
│
├── 2. PREPARE
│   ├── handler = tool.handler
│   ├── arguments = tool_call.arguments
│   └── effective_timeout = timeout or tool.timeout
│
├── 3. EXECUTION
│   ├── start_time = time.time()
│   │
│   ├── try:
│   │   ├── result = await asyncio.wait_for(
│   │   │       handler(**arguments),
│   │   │       timeout=effective_timeout
│   │   │   )
│   │   └── duration = time.time() - start_time
│   │
│   ├── except asyncio.TimeoutError:
│   │   └── return ToolResult(success=False, error="Timeout")
│   │
│   ├── except TypeError as e:  # Invalid arguments
│   │   └── return ToolResult(success=False, error=str(e))
│   │
│   └── except Exception as e:
│       ├── Log full traceback
│       └── return ToolResult(success=False, error=str(e))
│
├── 4. FORM RESULT
│   ├── If result is dict → serialize to JSON
│   ├── If result is str → use as is
│   └── Else → str(result)
│
├── 5. LOGGING
│   └── Log: tool_name, duration, success, error (if any)
│
└── 6. RETURN
    └── ToolResult(tool_call_id, content, success=True)
```

### Helper functions

```python
async def execute_tools(
    tool_calls: List[ToolCall],
    registry: ToolRegistry | None = None,
    parallel: bool = False
) -> List[ToolResult]:
    """
    Executes multiple tools.
    
    Args:
        tool_calls: List of calls
        parallel: Run in parallel (asyncio.gather)
                  or sequentially
                  
    Returns:
        List of results in same order
    """
```

### Error format for LLM

On execution error, a clear message is returned in `ToolResult.content`:

```python
ERROR_MESSAGES = {
    "not_found": "Tool '{name}' not found",
    "disabled": "Tool '{name}' is currently disabled",
    "timeout": "Tool '{name}' execution timed out after {timeout}s",
    "invalid_args": "Invalid arguments for tool '{name}': {error}",
    "execution": "Tool '{name}' failed: {error}"
}
```

### Done when
- [ ] execute_tool() executes tool
- [ ] Timeout works (asyncio.wait_for)
- [ ] Errors handled gracefully
- [ ] Result serialized correctly
- [ ] Call logging
- [ ] Tests for successful execution
- [ ] Tests for timeout
- [ ] Tests for errors

---

## Task 2.5: Plugin Base (tools/base.py)

### Description
Utilities for use in plugins: settings access, HTTP client, logging.

### File: tools/base.py

### Functions

#### Settings access
```python
def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    """
    Get plugin setting value.
    
    In Phase 2: returns default (DB settings in Phase 3)
    In Phase 3+: reads from DB
    
    Args:
        plugin_id: Plugin ID
        key: Setting key
        default: Default value
        
    Returns:
        Setting value or default
    """

def require_plugin_setting(plugin_id: str, key: str) -> Any:
    """
    Get required setting.
    
    Raises:
        PluginConfigError: If setting not set
    """
```

#### HTTP client
```python
def get_http_client(
    timeout: float = 30.0,
    follow_redirects: bool = True
) -> httpx.AsyncClient:
    """
    Get configured HTTP client.
    
    Returns:
        httpx.AsyncClient with preset timeouts
    """
```

#### Logging
```python
def get_plugin_logger(plugin_id: str) -> logging.Logger:
    """
    Get logger for plugin.
    
    Logger has [plugin_id] prefix in messages.
    
    Returns:
        logging.Logger
    """
```

#### Execution context (for future)
```python
@dataclass
class ToolContext:
    """Tool execution context"""
    user_id: str | None = None      # Telegram user ID
    chat_id: str | None = None      # Telegram chat ID
    plugin_id: str | None = None    # Plugin ID
    
# Global context (thread-local or contextvars)
_current_context: ToolContext | None = None

def get_current_context() -> ToolContext | None:
    """Get current execution context"""
    return _current_context
```

### Done when
- [ ] get_plugin_setting() works (returns default in Phase 2)
- [ ] get_http_client() returns configured client
- [ ] get_plugin_logger() returns logger with prefix
- [ ] Tests for utilities

---

## Task 2.6: Module public API (tools/__init__.py)

### Description
Export public functions and classes for use in other modules.

### File: tools/__init__.py

```python
"""
Tools — plugin system for LO_TG_BOT.

Usage:
    from tools import get_registry, load_all_plugins, execute_tool
    
    # Load plugins on startup
    await load_all_plugins()
    
    # Retrieving tools for LLM
    tools = get_registry().get_tools_for_llm()
    
    # Tool execution
    result = await execute_tool(tool_call)
"""

from tools.models import (
    ToolDefinition,
    ToolCall,
    ToolResult,
    PluginManifest,
)

from tools.registry import (
    ToolRegistry,
    get_registry,
)

from tools.loader import (
    load_all_plugins,
    load_plugin,
    reload_plugin,
    reload_all_plugins,
    LoadResult,
)

from tools.executor import (
    execute_tool,
    execute_tools,
)

from tools.base import (
    get_plugin_setting,
    require_plugin_setting,
    get_http_client,
    get_plugin_logger,
)

__all__ = [
    # Models
    "ToolDefinition",
    "ToolCall", 
    "ToolResult",
    "PluginManifest",
    
    # Registry
    "ToolRegistry",
    "get_registry",
    
    # Loader
    "load_all_plugins",
    "load_plugin",
    "reload_plugin",
    "reload_all_plugins",
    "LoadResult",
    
    # Executor
    "execute_tool",
    "execute_tools",
    
    # Base
    "get_plugin_setting",
    "require_plugin_setting",
    "get_http_client",
    "get_plugin_logger",
]
```

### Done when
- [ ] All public APIs exported
- [ ] Import `from tools import ...` works
- [ ] Docstring with usage example

---

## Task 2.7: Built-in Calculator plugin

### Description
Move calculator from hardcoded code to plugin.

### Structure
```
plugins/builtin/calculator/
├── plugin.yaml
└── handlers.py
```

### plugin.yaml
```yaml
id: calculator
name: "Calculator"
version: "1.0.0"
description: "Mathematical expression evaluator"
enabled: true

tools:
  - name: calculate
    description: "Evaluates a mathematical expression and returns the result. Supports: +, -, *, /, **, parentheses, sqrt, sin, cos, tan, log, abs, round, pi, e."
    handler: calculate
    timeout: 10
    parameters:
      type: object
      properties:
        expression:
          type: string
          description: "Mathematical expression to evaluate, e.g. '2 + 2 * 3' or 'sqrt(16) + pi'"
      required:
        - expression
```

### handlers.py
```python
"""Calculator plugin handlers."""

import math
import operator
from typing import Union

# Safe operations
SAFE_OPERATORS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '**': operator.pow,
    '%': operator.mod,
}

SAFE_FUNCTIONS = {
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log,
    'log10': math.log10,
    'abs': abs,
    'round': round,
    'floor': math.floor,
    'ceil': math.ceil,
}

SAFE_CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
}


async def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression.
    
    Args:
        expression: Expression to evaluate
        
    Returns:
        String with result or error message
    """
    try:
        # Use safe eval or simpleeval library
        result = _safe_eval(expression)
        
        # Format result
        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            return f"{result:.10g}"  # Strip trailing zeros
        return str(result)
        
    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: Cannot evaluate expression - {e}"


def _safe_eval(expression: str) -> Union[int, float]:
    """
    Safe expression evaluation.
    
    Implementation options:
    1. simpleeval library (recommended)
    2. ast.literal_eval + manual parsing
    3. Custom parser
    """
    # TODO: Implement via simpleeval or ast
    pass
```

### Done when
- [ ] plugin.yaml created and valid
- [ ] handlers.py implemented
- [ ] Safe evaluation (no code injection)
- [ ] Support basic operations: +, -, *, /, **
- [ ] Support functions: sqrt, sin, cos, tan, log
- [ ] Support constants: pi, e
- [ ] Correct error handling
- [ ] Tests

---

## Task 2.8: Built-in DateTime plugin

### Description
Move datetime tools from hardcoded code to plugin.

### Structure
```
plugins/builtin/datetime_tools/
├── plugin.yaml
└── handlers.py
```

### plugin.yaml
```yaml
id: datetime-tools
name: "Date & Time"
version: "1.0.0"
description: "Date and time utilities"
enabled: true

tools:
  - name: get_current_datetime
    description: "Returns current date and time with weekday name. Use this when user asks about current time or date."
    handler: get_current_datetime
    timeout: 5
    parameters:
      type: object
      properties:
        timezone:
          type: string
          description: "Timezone name (e.g. 'Europe/Moscow', 'UTC'). Default is server timezone."
      required: []

  - name: get_weekday
    description: "Returns the weekday name for a given date."
    handler: get_weekday
    timeout: 5
    parameters:
      type: object
      properties:
        date:
          type: string
          description: "Date in format YYYY-MM-DD, DD.MM.YYYY, or natural language like 'tomorrow', 'next monday'"
      required:
        - date

  - name: calculate_date_difference
    description: "Calculates the difference between two dates in days."
    handler: calculate_date_difference
    timeout: 5
    parameters:
      type: object
      properties:
        date1:
          type: string
          description: "First date"
        date2:
          type: string
          description: "Second date"
      required:
        - date1
        - date2
```

### handlers.py
```python
"""DateTime plugin handlers."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional


async def get_current_datetime(timezone: Optional[str] = None) -> str:
    """
    Returns current date and time.
    
    Args:
        timezone: Timezone (optional)
        
    Returns:
        String like "2024-01-15 14:30:00 (Monday)"
    """
    try:
        if timezone:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now()
        
        weekday = now.strftime("%A")
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        
        return f"{formatted} ({weekday})"
        
    except Exception as e:
        return f"Error: {e}"


async def get_weekday(date: str) -> str:
    """
    Returns weekday for given date.
    
    Args:
        date: Date in various formats
        
    Returns:
        Weekday name
    """
    try:
        parsed = _parse_date(date)
        if parsed is None:
            return f"Error: Cannot parse date '{date}'"
        
        weekday = parsed.strftime("%A")
        formatted = parsed.strftime("%Y-%m-%d")
        
        return f"{formatted} is {weekday}"
        
    except Exception as e:
        return f"Error: {e}"


async def calculate_date_difference(date1: str, date2: str) -> str:
    """
    Computes difference between dates in days.
    """
    try:
        d1 = _parse_date(date1)
        d2 = _parse_date(date2)
        
        if d1 is None:
            return f"Error: Cannot parse date '{date1}'"
        if d2 is None:
            return f"Error: Cannot parse date '{date2}'"
        
        diff = abs((d2 - d1).days)
        return f"{diff} days"
        
    except Exception as e:
        return f"Error: {e}"


def _parse_date(date_str: str) -> Optional[datetime]:
    """
    Parses date from various formats.
    
    Supports:
    - YYYY-MM-DD
    - DD.MM.YYYY
    - DD/MM/YYYY
    - today, tomorrow, yesterday
    """
    date_str = date_str.strip().lower()
    
    # Special values
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_str == 'today':
        return today
    elif date_str == 'tomorrow':
        return today + timedelta(days=1)
    elif date_str == 'yesterday':
        return today - timedelta(days=1)
    
    # Date formats
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None
```

### Done when
- [ ] plugin.yaml created and valid
- [ ] get_current_datetime works
- [ ] get_weekday works with different formats
- [ ] calculate_date_difference works
- [ ] Timezone support
- [ ] Support special values (today, tomorrow)
- [ ] Tests

---

## Task 2.9: Integration with tool_calling.py

### Description
Modify `bot/tool_calling.py` to use Registry and Executor instead of hardcoded tools.

### Changes in bot/tool_calling.py

**Before (Phase 1):**
```python
# Hardcoded tools
HARDCODED_TOOLS = [...]

async def get_reply_with_tools(messages):
    tools = HARDCODED_TOOLS
    ...
    # Execution via local functions
    result = await execute_hardcoded_tool(tool_call)
```

**After (Phase 2):**
```python
from tools import get_registry, execute_tool, load_all_plugins

# On first call load plugins
_plugins_loaded = False

async def _ensure_plugins_loaded():
    global _plugins_loaded
    if not _plugins_loaded:
        await load_all_plugins()
        _plugins_loaded = True


async def get_reply_with_tools(messages):
    await _ensure_plugins_loaded()
    
    registry = get_registry()
    tools = registry.get_tools_for_llm()
    
    if not tools:
        # No tools — regular reply
        return await get_reply(messages)
    
    ...
    
    # Execution via Executor
    for tool_call in tool_calls:
        result = await execute_tool(tool_call)
        ...
```

### Remove hardcoded code
- Remove `HARDCODED_TOOLS`
- Remove local functions `get_current_datetime()`, `calculate()`
- Remove local function `execute_hardcoded_tool()`

### Done when
- [ ] tool_calling.py uses Registry
- [ ] tool_calling.py uses Executor
- [ ] Hardcoded code removed
- [ ] Plugins loaded on first call
- [ ] Tests pass
- [ ] Manual testing: "What time?" and "Calculate 2+2"

---

## Task 2.10: Phase 2 testing

### Unit tests

#### tests/test_tools_models.py
```
test_tool_definition_validation
test_plugin_manifest_validation
test_tool_call_creation
test_tool_result_creation
```

#### tests/test_tools_registry.py
```
test_register_tool
test_register_duplicate_tool_raises
test_get_tool
test_get_tool_not_found
test_get_enabled_tools
test_get_tools_for_llm_format
test_enable_disable_tool
test_unregister_plugin
test_clear_registry
test_singleton_pattern
```

#### tests/test_tools_loader.py
```
test_load_all_plugins
test_load_plugin_success
test_load_plugin_missing_yaml
test_load_plugin_invalid_yaml
test_load_plugin_missing_handler
test_reload_plugin
test_reload_all_plugins
test_ignore_pycache_dirs
```

#### tests/test_tools_executor.py
```
test_execute_tool_success
test_execute_tool_not_found
test_execute_tool_disabled
test_execute_tool_timeout
test_execute_tool_exception
test_execute_tool_invalid_args
test_execute_tools_parallel
test_execute_tools_sequential
```

#### tests/test_builtin_plugins.py
```
# Calculator
test_calculate_basic_operations
test_calculate_functions
test_calculate_constants
test_calculate_division_by_zero
test_calculate_invalid_expression
test_calculate_safe_from_injection

# DateTime
test_get_current_datetime
test_get_current_datetime_with_timezone
test_get_weekday_iso_format
test_get_weekday_dot_format
test_get_weekday_special_values
test_calculate_date_difference
```

### Integration tests

```
test_full_flow_calculator_through_llm
test_full_flow_datetime_through_llm
test_plugins_reload_updates_registry
```

### Manual testing (checklist)

**Setup:**
- [ ] Plugins in plugins/builtin/ folder
- [ ] Bot running
- [ ] LLM configured

**Calculator:**
- [ ] "What is 2+2?" → "4"
- [ ] "15% of 200" → "30"
- [ ] "Square root of 144" → "12"
- [ ] "sin(0) + cos(0)" → "1"
- [ ] "Divide 10 by 0" → error message

**DateTime:**
- [ ] "What time is it?" → current time
- [ ] "What day of the week is it?" → correct day
- [ ] "What day is 01.01.2025?" → Wednesday
- [ ] "Days until New Year?" → correct number

**Regular questions (no tools):**
- [ ] "Hi!" → normal reply
- [ ] "Tell a joke" → normal reply

### Done when
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing done
- [ ] No regressions

---

## Work sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 1: Models and Registry                                                  │
│                                                                             │
│  Morning:                                                                      │
│  ├── 2.1 Create tools/models.py                                           │
│  └── Model tests                                                         │
│                                                                             │
│  Afternoon:                                                               │
│  ├── 2.2 Create tools/registry.py                                         │
│  └── Registry tests                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 2: Loader                                                             │
│                                                                             │
│  ├── 2.3 Create tools/loader.py                                           │
│  ├── Folder scanning                                                    │
│  ├── YAML parsing                                                          │
│  ├── Loading handlers via importlib                                     │
│  └── Loader tests                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 3: Executor and Base                                                    │
│                                                                             │
│  Morning:                                                                      │
│  ├── 2.4 Create tools/executor.py                                         │
│  └── Executor tests                                                        │
│                                                                             │
│  Afternoon:                                                               │
│  ├── 2.5 Create tools/base.py                                             │
│  ├── 2.6 Create tools/__init__.py                                         │
│  └── Base tests                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 4: Built-in plugins                                                    │
│                                                                             │
│  Morning:                                                                      │
│  ├── 2.7 Create plugins/builtin/calculator/                               │
│  └── Calculator tests                                                      │
│                                                                             │
│  Afternoon:                                                               │
│  ├── 2.8 Create plugins/builtin/datetime_tools/                           │
│  └── Datetime tests                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 5: Integration and testing                                         │
│                                                                             │
│  Morning:                                                                      │
│  ├── 2.9 Integration with tool_calling.py                                      │
│  └── Remove hardcoded code                                         │
│                                                                             │
│  Afternoon:                                                               │
│  ├── 2.10 Integration tests                                                │
│  ├── Manual testing                                                   │
│  └── Bug fixes                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2 RESULT                                                          │
│                                                                             │
│  ✅ Plugin System works                                                     │
│  ✅ Plugins load from plugins/ folder                                       │
│  ✅ Calculator and DateTime are full plugins                               │
│  ✅ Adding a plugin = adding files                                          │
│  ✅ Hot-reload plugins (programmatic)                                       │
│  ✅ Foundation ready for Phase 3 (Storage + API)                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## External library dependencies

### New dependencies (add to requirements.txt)

```
PyYAML>=6.0           # Parse plugin.yaml
simpleeval>=0.9.13    # Safe expression evaluation (for calculator)
```

### Existing (already in use)
```
pydantic              # Model validation
httpx                 # HTTP client (in base.py)
```

---

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-------------|
| importlib fails to load module | Medium | High | Detailed logging, tests |
| Circular imports | Medium | Medium | Lazy imports, architecture |
| YAML parsing fails | Low | Medium | Pydantic validation, try-except |
| simpleeval unsafe | Low | High | Limit functions, injection tests |
| Plugin breaks entire bot | Medium | High | Error isolation, fallback |

---

## Definition of Done for Phase 2

- [ ] All tasks 2.1–2.10 done
- [ ] tools/ module created and works
- [ ] Built-in plugins work
- [ ] Hardcoded tools removed
- [ ] All tests pass
- [ ] Manual testing done
- [ ] No regressions
- [ ] Code reviewed
- [ ] Documentation updated

---

## Out of scope for Phase 2

- ❌ Storing plugin settings in DB (Phase 3)
- ❌ API for plugin management (Phase 3)
- ❌ UI for plugin management (Phase 4)
- ❌ Business plugins (Worklog Checker, etc.) (Phase 6)

---

## Document versioning

| Version | Date | Description |
|--------|------|----------|
| 1.0 | 2026-02-06 | First version of Phase 2 detailed plan |
