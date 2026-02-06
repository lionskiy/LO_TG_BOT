# PHASE 3: Storage + API

> **Detailed task breakdown for Phase 3**  
> Storing plugin settings in DB and API for tool management

**Version:** 1.0  
**Date:** 2026-02-06  
**Estimated duration:** 3-5 days  
**Prerequisite:** Phase 2 done (Plugin System works)

---

## Related documents

| Document | Description | Status |
|----------|----------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target system architecture | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Task breakdown | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Phase 0-1 | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Phase 2 | ✅ Current (in progress) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Phase 3 (this document) | ✅ Current (in progress) |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Phase 4 (next) | ✅ Current (in progress) |

### Current implementation (v1.0)

| Document | Description |
|----------|----------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Current implementation spec |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

---

## Phase navigation

| Phase | Document | Description | Status |
|------|----------|----------|--------|
| 0-1 | [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Stabilization + Tool-Calling | ✅ Current (in progress) |
| 2 | [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Plugin System | ✅ Current (in progress) |
| 3 | **[PLAN_PHASE_3.md](PLAN_PHASE_3.md)** | Storage + API | ✅ Current (in progress) |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Admin Tools | ✅ Current (in progress) |
| 5 | [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Admin Administrators | ✅ Current (in progress) |
| 6 | [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Worklog Checker | ✅ Current (in progress) |

---

## Phase 3

**Before (after Phase 2):** Plugin System works but plugin settings are not saved. On restart everything resets.

**After:** Plugin settings (enabled/disabled, credentials, parameters) are stored in DB. There is an API for managing tools and their settings.

**Important:** 
- Use existing infrastructure (SQLite, encryption.py)
- API protected X-Admin-Key (as existing endpoints)
- Secrets encrypted (Fernet, as Telegram/LLM tokens)

---

## Phase 3

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Admin Panel (Phase 4)                                                       │
│       │                                                                     │
│       │  HTTP                                                               │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │  Admin API (FastAPI)                                                    │
│  │                                                                         │
│  │  Existing routes:                                                  │
│  │  ├── /api/settings/telegram/*                                          │
│  │  ├── /api/settings/llm/*                                               │
│  │  └── /api/service-admins/*                                             │
│  │                                                                         │
│  │  New routes:                              [PHASE 3]                   │
│  │  ├── /api/tools/*          ← tools_router.py                           │
│  │  └── /api/plugins/*        ← plugins_router.py                         │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
│       │                               │
│       │                               │
│       ▼                               ▼
│  ┌───────────────────┐      ┌───────────────────────────────────────────┐
│  │  Tools Repository │      │  Plugin Settings Manager                  │
│  │                   │      │  (tools/settings_manager.py)              │
│  │  • CRUD operations  │◄────►│                                           │
│  │  • Encryption     │      │  • get_settings()                         │
│  │                   │      │  • save_settings()                        │
│  └───────────────────┘      │  • validate_settings()                    │
│       │                      │  • sync_with_registry()                   │
│       │                      └───────────────────────────────────────────┘
│       ▼                               │
│  ┌───────────────────┐               │
│  │  SQLite           │               │
│  │                   │               ▼
│  │  tool_settings    │      ┌───────────────────────────────────────────┐
│  │  ├── tool_name    │      │  Tool Registry (from Phase 2)                │
│  │  ├── plugin_id    │      │                                           │
│  │  ├── enabled      │◄────►│  • Sync enabled statuses        │
│  │  ├── settings_json│      │  • Get schema for validation        │
│  │  └── updated_at   │      │                                           │
│  │                   │      └───────────────────────────────────────────┘
│  └───────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## New/modified files

```
LO_TG_BOT/
├── api/
│   ├── db.py                   # [EXTENSION] Add ToolSettingsModel
│   ├── tools_repository.py     # [NEW] CRUD for tool_settings
│   ├── tools_router.py         # [NEW] API /api/tools/*
│   ├── plugins_router.py       # [NEW] API /api/plugins/*
│   └── app.py                  # [EXTENSION] Wire routers, startup
│
├── tools/
│   └── settings_manager.py     # [EXTENSION] DB integration
│
└── tests/
    ├── test_tools_repository.py
    ├── test_tools_router.py
    └── test_plugins_router.py
```

---

# Phase 3

---

## Task 3.1: ToolSettingsModel data model

### Description
Add SQLAlchemy model for storing tool settings in existing DB.

### File: api/db.py (extension)

### ToolSettingsModel model

```python
class ToolSettingsModel(Base):
    """
    Tool/plugin settings.
    
    Stores:
    - Enabled status
    - Plugin settings (settings_json) — encrypted
    """
    __tablename__ = "tool_settings"
    
    # Primary key — tool name
    tool_name = Column(String, primary_key=True)
    
    # Owner plugin ID (for grouping)
    plugin_id = Column(String, nullable=False, index=True)
    
    # Whether tool is enabled
    enabled = Column(Boolean, default=False, nullable=False)
    
    # Settings in JSON (Fernet encrypted)
    # Format: {"jira_url": "...", "jira_token": "..."}
    settings_json = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Migration

Table created automatically on startup (like existing tables):

```python
# In init_db() or create_tables()
Base.metadata.create_all(bind=engine)
```

**Important:** Existing tables (telegram_settings, llm_settings, service_admins) are not modified.

### Indexes

```python
# Index for fast lookup by plugin_id
Index('ix_tool_settings_plugin_id', ToolSettingsModel.plugin_id)
```

### Done when
- [ ] Model added to api/db.py
- [ ] Table created on startup
- [ ] Existing tables not broken
- [ ] Test create/read record

---

## Task 3.2: Tools Repository

### Description
Data access layer for tool_settings. Encapsulates CRUD and encryption.

### File: api/tools_repository.py (new)

### Functions

#### Read
```python
def get_tool_settings(tool_name: str) -> ToolSettingsModel | None:
    """
    Get tool settings by name.
    
    Args:
        tool_name: Tool name
        
    Returns:
        Model with decrypted settings or None
    """

def get_all_tool_settings() -> List[ToolSettingsModel]:
    """
    Get all tool settings.
    
    Returns:
        List of models (settings decrypted)
    """

def get_tool_settings_by_plugin(plugin_id: str) -> List[ToolSettingsModel]:
    """
    Get settings for tools of a specific plugin.
    """
```

#### Write
```python
def save_tool_settings(
    tool_name: str,
    plugin_id: str,
    enabled: bool = False,
    settings: dict | None = None
) -> ToolSettingsModel:
    """
    Save tool settings (create or update).
    
    Args:
        tool_name: Tool name
        plugin_id: Plugin ID
        enabled: Whether enabled
        settings: Settings dict (will be encrypted)
        
    Returns:
        Saved model
    """

def update_tool_enabled(tool_name: str, enabled: bool) -> bool:
    """
    Update only enabled status.
    
    Returns:
        True if successful, False if not found
    """

def update_tool_settings(tool_name: str, settings: dict) -> bool:
    """
    Update only settings (without changing enabled).
    
    Returns:
        True if successful, False if not found
    """
```

#### Delete
```python
def delete_tool_settings(tool_name: str) -> bool:
    """
    Delete tool settings.
    
    Returns:
        True if deleted, False if not found
    """

def delete_plugin_settings(plugin_id: str) -> int:
    """
    Delete settings for all tools of a plugin.
    
    Returns:
        Number of deleted records
    """
```

### Encryption

Use existing `api/encryption.py`:

```python
from api.encryption import encrypt_value, decrypt_value

def _encrypt_settings(settings: dict) -> str:
    """Encrypt settings to JSON string"""
    json_str = json.dumps(settings, ensure_ascii=False)
    return encrypt_value(json_str)

def _decrypt_settings(encrypted: str) -> dict:
    """Decrypt settings from JSON string"""
    json_str = decrypt_value(encrypted)
    return json.loads(json_str)
```

### Masking for API

```python
def mask_settings(
    settings: dict, 
    schema: List[PluginSettingDefinition]
) -> dict:
    """
    Mask secret fields for API response.
    
    Fields with type='password' masked as '***xxxxx' (last 5 chars).
    
    Args:
        settings: Decrypted settings
        schema: Settings schema from plugin.yaml
        
    Returns:
        Settings with masked passwords
    """
    
def _mask_value(value: str) -> str:
    """Masks value, keeping last 5 chars"""
    if not value or len(value) <= 5:
        return "***"
    return f"***{value[-5:]}"
```

### Session handling

Use pattern from existing code:

```python
from api.db import SessionLocal

def get_tool_settings(tool_name: str) -> ToolSettingsModel | None:
    with SessionLocal() as session:
        result = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.tool_name == tool_name
        ).first()
        
        if result and result.settings_json:
            # Decrypt before return
            result._decrypted_settings = _decrypt_settings(result.settings_json)
        
        return result
```

### Done when
- [ ] All CRUD functions implemented
- [ ] Encryption works (uses encryption.py)
- [ ] Masking works
- [ ] Tests for all operations
- [ ] Tests for encrypt/decrypt

---

## Task 3.3: Plugin Settings Manager (extension)

### Description
Extend `tools/settings_manager.py` to use DB instead of stubs.

### File: tools/settings_manager.py (extension from Phase 2)

### Before (Phase 2)

```python
def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    # Stub — always returns default
    return default
```

### After (Phase 3)

```python
from api.tools_repository import get_tool_settings, save_tool_settings

def get_plugin_settings(plugin_id: str) -> dict:
    """
    Get all plugin settings from DB.
    
    Args:
        plugin_id: Plugin ID
        
    Returns:
        Settings dict or empty dict
    """
    # Get settings of plugin's first tool
    # (all plugin tools share settings)
    from tools import get_registry
    registry = get_registry()
    
    tools = registry.get_tools_by_plugin(plugin_id)
    if not tools:
        return {}
    
    tool_name = tools[0].name
    record = get_tool_settings(tool_name)
    
    if record and hasattr(record, '_decrypted_settings'):
        return record._decrypted_settings
    
    return {}


def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    """
    Get a specific plugin setting.
    """
    settings = get_plugin_settings(plugin_id)
    return settings.get(key, default)


def save_plugin_settings(plugin_id: str, settings: dict) -> None:
    """
    Save plugin settings.
    Saves for all plugin tools.
    """
    from tools import get_registry
    registry = get_registry()
    
    tools = registry.get_tools_by_plugin(plugin_id)
    
    for tool in tools:
        save_tool_settings(
            tool_name=tool.name,
            plugin_id=plugin_id,
            enabled=tool.enabled,
            settings=settings
        )


def is_plugin_configured(plugin_id: str) -> bool:
    """
    Check that all required settings are set.
    """
    from tools import get_registry
    registry = get_registry()
    
    manifest = registry.get_plugin(plugin_id)
    if not manifest or not manifest.settings:
        return True  # No settings — consider configured
    
    settings = get_plugin_settings(plugin_id)
    
    for setting_def in manifest.settings:
        if setting_def.required:
            value = settings.get(setting_def.key)
            if value is None or value == "":
                return False
    
    return True


def get_missing_settings(plugin_id: str) -> List[str]:
    """
    Get list of missing required settings.
    """
    from tools import get_registry
    registry = get_registry()
    
    manifest = registry.get_plugin(plugin_id)
    if not manifest or not manifest.settings:
        return []
    
    settings = get_plugin_settings(plugin_id)
    missing = []
    
    for setting_def in manifest.settings:
        if setting_def.required:
            value = settings.get(setting_def.key)
            if value is None or value == "":
                missing.append(setting_def.key)
    
    return missing


def validate_plugin_settings(settings: dict, schema: List) -> List[dict]:
    """
    Validate settings against schema.
    
    Returns:
        List of errors [{"field": "...", "error": "..."}] or []
    """
    errors = []
    
    for setting_def in schema:
        key = setting_def.key
        value = settings.get(key)
        
        # Check required
        if setting_def.required and (value is None or value == ""):
            # Skip masked passwords
            if not (isinstance(value, str) and value.startswith("***")):
                errors.append({"field": key, "error": "Required field is empty"})
                continue
        
        # Check type
        if value is not None and value != "":
            if setting_def.type == "number":
                if not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except:
                        errors.append({"field": key, "error": "Must be a number"})
            
            elif setting_def.type == "boolean":
                if not isinstance(value, bool):
                    errors.append({"field": key, "error": "Must be true or false"})
    
    return errors
```

### Sync with Registry

```python
async def sync_settings_with_registry() -> None:
    """
    Sync settings from DB to Registry.
    Called on application startup after loading plugins.
    """
    from tools import get_registry
    from api.tools_repository import get_all_tool_settings
    
    registry = get_registry()
    db_settings = get_all_tool_settings()
    
    for record in db_settings:
        tool = registry.get_tool(record.tool_name)
        if tool:
            if record.enabled:
                registry.enable_tool(record.tool_name)
            else:
                registry.disable_tool(record.tool_name)
```

### Done when
- [ ] get_plugin_settings() reads from DB
- [ ] save_plugin_settings() writes to DB
- [ ] is_plugin_configured() checks required fields
- [ ] validate_plugin_settings() validates
- [ ] sync_settings_with_registry() works
- [ ] Tests

---

## Task 3.4: Tools Router (API)

### Description
REST API for managing tools: list, enable/disable, settings.

### File: api/tools_router.py (new)

### Endpoints

---

#### GET /api/tools — Tool list

**Description:** Get list of all tools with their statuses.

**Response 200:**
```json
{
  "tools": [
    {
      "name": "calculate",
      "description": "Evaluates mathematical expression...",
      "plugin_id": "calculator",
      "plugin_name": "Calculator",
      "enabled": true,
      "needs_config": false,
      "has_settings": false
    },
    {
      "name": "check_worklogs",
      "description": "Checks employee worklogs...",
      "plugin_id": "worklog-checker",
      "plugin_name": "Worklog Checker",
      "enabled": false,
      "needs_config": true,
      "has_settings": true
    }
  ],
  "total": 2,
  "enabled_count": 1
}
```

---

#### GET /api/tools/{name} — Tool details

**Description:** Get full tool information.

**Response 200:**
```json
{
  "name": "check_worklogs",
  "description": "Checks employee worklogs for specified period",
  "plugin_id": "worklog-checker",
  "plugin_name": "Worklog Checker",
  "plugin_version": "1.0.0",
  "enabled": false,
  "needs_config": true,
  "parameters": {
    "type": "object",
    "properties": {
      "employee": {"type": "string", "description": "Employee name"},
      "period": {"type": "string", "description": "Period (week, month)"}
    },
    "required": ["employee"]
  },
  "settings_schema": [
    {
      "key": "jira_url",
      "label": "Jira URL",
      "type": "string",
      "required": true,
      "description": "Base URL of Jira instance"
    },
    {
      "key": "jira_token",
      "label": "Jira API Token",
      "type": "password",
      "required": true
    }
  ],
  "current_settings": {
    "jira_url": "https://jira.company.com",
    "jira_token": "***abc12"
  },
  "missing_settings": ["tempo_token"]
}
```

**Response 404:**
```json
{
  "detail": "Tool 'unknown_tool' not found"
}
```

---

#### POST /api/tools/{name}/enable — Enable tool

**Description:** Enable tool. Checks that settings are filled.

**Response 200:**
```json
{
  "success": true,
  "message": "Tool 'calculate' enabled"
}
```

**Response 400 (settings required):**
```json
{
  "success": false,
  "message": "Tool 'check_worklogs' requires configuration",
  "missing_settings": ["jira_url", "jira_token", "tempo_token"]
}
```

---

#### POST /api/tools/{name}/disable — Disable tool

**Response 200:**
```json
{
  "success": true,
  "message": "Tool 'calculate' disabled"
}
```

---

#### GET /api/tools/{name}/settings — Get settings

**Response 200:**
```json
{
  "plugin_id": "worklog-checker",
  "settings": {
    "jira_url": "https://jira.company.com",
    "jira_token": "***abc12",
    "required_hours": 8
  },
  "schema": [...]
}
```

---

#### PUT /api/tools/{name}/settings — Save settings

**Request:**
```json
{
  "settings": {
    "jira_url": "https://jira.company.com",
    "jira_token": "new-secret-token",
    "required_hours": 8
  }
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Settings saved"
}
```

**Response 400 (validation error):**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {"field": "jira_url", "error": "Required field is empty"},
    {"field": "required_hours", "error": "Must be a number"}
  ]
}
```

**Note:** If field with type=password is sent as `"***..."` (mask), it is not updated.

---

#### POST /api/tools/{name}/test — Test connection

**Response 200:**
```json
{
  "success": true,
  "message": "Connection successful",
  "details": {
    "jira": "OK",
    "tempo": "OK"
  }
}
```

**Response 400 (not supported):**
```json
{
  "success": false,
  "message": "Tool 'calculate' does not support connection testing"
}
```

### Done when
- [ ] GET /api/tools works
- [ ] GET /api/tools/{name} works
- [ ] POST /api/tools/{name}/enable works
- [ ] POST /api/tools/{name}/disable works
- [ ] GET /api/tools/{name}/settings works
- [ ] PUT /api/tools/{name}/settings works
- [ ] POST /api/tools/{name}/test works
- [ ] Auth via X-Admin-Key
- [ ] Swagger documentation
- [ ] Tests for all endpoints

---

## Task 3.5: Plugins Router (API)

### Description
API for managing plugins: list, reload.

### File: api/plugins_router.py (new)

### Endpoints

---

#### GET /api/plugins — List plugins

**Response 200:**
```json
{
  "plugins": [
    {
      "id": "calculator",
      "name": "Calculator",
      "version": "1.0.0",
      "description": "Mathematical expression evaluator",
      "tools_count": 1,
      "enabled_count": 1
    },
    {
      "id": "datetime-tools",
      "name": "Date & Time",
      "version": "1.0.0",
      "description": "Date and time utilities",
      "tools_count": 3,
      "enabled_count": 2
    }
  ],
  "total": 2
}
```

---

#### POST /api/plugins/reload — Reload all plugins

**Response 200:**
```json
{
  "success": true,
  "message": "Plugins reloaded",
  "loaded": ["calculator", "datetime-tools"],
  "failed": [],
  "total_tools": 4
}
```

---

#### POST /api/plugins/{id}/reload — Reload one plugin

**Response 200:**
```json
{
  "success": true,
  "message": "Plugin 'calculator' reloaded",
  "tools_count": 1
}
```

**Response 404:**
```json
{
  "detail": "Plugin 'unknown' not found"
}
```

### Done when
- [ ] GET /api/plugins works
- [ ] POST /api/plugins/reload works
- [ ] POST /api/plugins/{id}/reload works
- [ ] Sync with DB after reload
- [ ] Tests

---

## Task 3.6: Integration in app.py

### Description
Wire new routers and configure plugin loading on startup.

### File: api/app.py (extension)

### Changes

#### Wire routers

```python
from api.tools_router import router as tools_router
from api.plugins_router import router as plugins_router

# After existing routers
app.include_router(tools_router)
app.include_router(plugins_router)
```

#### Startup event

```python
@app.on_event("startup")
async def startup_event():
    # Existing logic...
    
    # NEW: Load plugins
    from tools import load_all_plugins
    from tools.settings_manager import sync_settings_with_registry
    
    logger.info("Loading plugins...")
    result = await load_all_plugins()
    logger.info(f"Loaded {len(result.loaded)} plugins with {result.total_tools} tools")
    
    if result.failed:
        for error in result.failed:
            logger.error(f"Failed to load plugin: {error.plugin_path} - {error.error}")
    
    # Sync settings from DB
    await sync_settings_with_registry()
    logger.info("Plugin settings synchronized with database")
```

### Initialization order

```
app startup:
│
├── 1. DB init (existing)
│   └── create_tables()
│
├── 2. Load plugins (NEW)
│   ├── load_all_plugins()
│   └── Plugins registered in Registry
│
├── 3. Sync settings (NEW)
│   ├── sync_settings_with_registry()
│   └── enabled statuses from DB → Registry
│
├── 4. Start bot (existing)
│   └── start_bot_subprocess()
│
└── 5. Ready to accept requests
```

### Done when
- [ ] Routers wired
- [ ] Plugins load on startup
- [ ] Settings synced
- [ ] Logging
- [ ] Existing functionality not broken

---

## Task 3.7: Phase 3 testing

### Unit tests

#### tests/test_tools_repository.py
```
test_save_tool_settings_new
test_save_tool_settings_update
test_get_tool_settings
test_get_tool_settings_not_found
test_get_all_tool_settings
test_update_tool_enabled
test_delete_tool_settings
test_encryption_decryption
test_mask_settings
```

#### tests/test_settings_manager.py
```
test_get_plugin_settings
test_get_plugin_setting_with_default
test_save_plugin_settings
test_is_plugin_configured_true
test_is_plugin_configured_false
test_get_missing_settings
test_validate_plugin_settings
test_sync_settings_with_registry
```

#### tests/test_tools_router.py
```
test_list_tools
test_get_tool
test_get_tool_not_found
test_enable_tool
test_enable_tool_needs_config
test_disable_tool
test_get_settings
test_update_settings
test_update_settings_validation_error
test_update_settings_preserve_masked_passwords
test_test_connection
```

#### tests/test_plugins_router.py
```
test_list_plugins
test_reload_all_plugins
test_reload_one_plugin
test_reload_one_plugin_not_found
```

### Manual testing (checklist)

**API check via Swagger (/docs):**
- [ ] GET /api/tools — returns list
- [ ] GET /api/tools/calculate — returns details
- [ ] POST /api/tools/calculate/enable — enables
- [ ] POST /api/tools/calculate/disable — disables
- [ ] PUT /api/tools/{name}/settings — saves
- [ ] GET /api/plugins — returns plugin list
- [ ] POST /api/plugins/reload — reloads

**Persistence check:**
- [ ] Enable tool → restart → check still enabled
- [ ] Save settings → restart → check saved

**Encryption check:**
- [ ] Look in DB — settings_json encrypted
- [ ] API returns decrypted (with mask for passwords)

### Done when
- [ ] All unit tests pass
- [ ] Manual testing done
- [ ] No regressions

---

## Work sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 1: Storage                                                            │
│                                                                             │
│  Morning:                                                                      │
│  ├── 3.1 ToolSettingsModel model in db.py                                  │
│  └── Test table creation                                                 │
│                                                                             │
│  Afternoon:                                                               │
│  ├── 3.2 Tools Repository                                                  │
│  └── Tests CRUD and encryption                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 2: Settings Manager + API (part 1)                                   │
│                                                                             │
│  Morning:                                                                      │
│  ├── 3.3 Extend settings_manager.py                                    │
│  └── Tests settings_manager                                                │
│                                                                             │
│  Afternoon:                                                               │
│  ├── 3.4 Tools Router (GET /api/tools, GET /api/tools/{name})              │
│  └── Tests                                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 3: API (part 2) + Integration                                        │
│                                                                             │
│  Morning:                                                                      │
│  ├── 3.4 Tools Router (enable, disable, settings, test)                    │
│  └── Tests                                                                 │
│                                                                             │
│  Afternoon:                                                               │
│  ├── 3.5 Plugins Router                                                    │
│  ├── 3.6 Integration in app.py                                               │
│  └── Tests                                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 4: Testing                                                      │
│                                                                             │
│  ├── 3.7 Manual testing by checklist                                   │
│  ├── Bug fixes                                                     │
│  └── API documentation (Swagger)                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3 RESULT                                                          │
│                                                                             │
│  ✅ Plugin settings stored in DB                                    │
│  ✅ Secrets encrypted                                                     │
│  ✅ API for managing tools works                              │
│  ✅ API for managing plugins works                                  │
│  ✅ Persistence: settings survive restart                       │
│  ✅ Backend ready for Phase 4 (Admin Tools)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Summary

### Tools Router (/api/tools)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/tools | Tool list |
| GET | /api/tools/{name} | Tool details |
| POST | /api/tools/{name}/enable | Enable |
| POST | /api/tools/{name}/disable | Disable |
| GET | /api/tools/{name}/settings | Get settings |
| PUT | /api/tools/{name}/settings | Save settings |
| POST | /api/tools/{name}/test | Test connection |

### Plugins Router (/api/plugins)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/plugins | List plugins |
| POST | /api/plugins/reload | Reload all |
| POST | /api/plugins/{id}/reload | Reload one |

---

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-------------|---------|-----------|
| DB migration breaks data | Low | High | New table, do not touch existing |
| Encryption incompatible | Low | Medium | Use existing encryption.py |
| Race on parallel requests | Medium | Medium | SQLAlchemy transactions |

---

## Definition of Done for Phase 3

- [ ] All tasks 3.1-3.7 done
- [ ] ToolSettingsModel created
- [ ] Repository works
- [ ] Settings Manager integrated with DB
- [ ] Tools Router implemented
- [ ] Plugins Router implemented
- [ ] Integration in app.py done
- [ ] All tests pass
- [ ] Manual testing done
- [ ] Swagger docs up to date
- [ ] No regressions

---

## Out of scope for Phase 3

- ❌ Admin UI (Phase 4)
- ❌ Business plugins (Phase 6)

---

## Document versioning

| Version | Date | Description |
|--------|------|----------|
| 1.0 | 2026-02-06 | First version of Phase 3 detailed plan |
