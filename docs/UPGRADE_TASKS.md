# UPGRADE TASKS — LO_TG_BOT

> **Task breakdown for project evolution**  
> Detailed to 3–4 levels for planning and tracking

**Version:** 1.1  
**Date:** 2026-02-06

---

## Related documents

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target system architecture | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Task breakdown (this document) | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Detailed plan for Phase 0–1 | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Detailed plan for Phase 2 (Plugin System) | ✅ Current (in progress) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Detailed plan for Phase 3 (Storage + API) | ✅ Current (in progress) |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Detailed plan for Phase 4 (Admin Tools) | ✅ Current (in progress) |
| [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Detailed plan for Phase 5 (Admin Administrators) | ✅ Current (in progress) |
| [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Detailed plan for Phase 6 (Worklog Checker) | ✅ Current (in progress) |
| [SPEC_HR_SERVICE.md](SPEC_HR_SERVICE.md) | Спецификация плагина HR Service | ✅ Current |
| [PLAN_HR_SERVICE.md](PLAN_HR_SERVICE.md) | План работ HR Service (задачи с чекбоксами) | ✅ Current |

### Current state (v1.0) — implemented

| Document | Description |
|----------|-------------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Full specification of current implementation |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

---

## How to use this document

1. **When planning a sprint** — pick a block/subblock from the required phase
2. **When developing** — check against the done criteria
3. **When doing code review** — verify all sub-items are done
4. **When testing** — use the done criteria as a checklist
5. **Detailed phase plan** — see the corresponding PLAN_PHASE_X.md
6. **Architecture questions** — see [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md)
7. **Терминология:** плагин = инструмент для оркестратора; у плагина — функции (не инструменты). См. раздел "Terminology" в ARCHITECTURE_BLUEPRINT.

---

## Functional blocks (full breakdown)

---

## 1. LLM ENGINE (Orchestrator) — EXTENSION

```
1. LLM ENGINE
│
├── 1.1 LLM Router [NEW]
│   │
│   ├── 1.1.1 Request building
│   │   ├── Build system_prompt (English)
│   │   ├── Get tools from Registry
│   │   ├── Add conversation history
│   │   └── Add user message
│   │
│   ├── 1.1.2 LLM response handling
│   │   ├── Check for tool_calls
│   │   ├── Parse function name and arguments
│   │   ├── Call Tool Executor
│   │   └── Build tool_result message
│   │
│   ├── 1.1.3 Tool-calling loop
│   │   ├── Follow-up request to LLM with result
│   │   ├── Support multiple tool calls
│   │   ├── Depth limit (max iterations)
│   │   └── Get final text reply
│   │
│   ├── 1.1.4 Error handling
│   │   ├── Tool not found
│   │   ├── Tool execution error
│   │   ├── LLM timeout/error
│   │   └── Fallback to normal reply
│   │
│   ├── Files:
│   │   └── bot/tool_calling.py [NEW]
│   │
│   ├── Dependencies: Tool Registry, Tool Executor
│   │
│   └── Done when:
│       └── LLM selects and calls tools, returns reply
│
├── 1.2 LLM Provider Adapter [EXTENSION]
│   │
│   ├── 1.2.1 OpenAI / OpenAI-compatible
│   │   ├── Add tools parameter to request
│   │   ├── Add tool_choice parameter
│   │   ├── Handle response.tool_calls
│   │   └── Build tool result message
│   │
│   ├── 1.2.2 Anthropic (Claude)
│   │   ├── Convert tools to Anthropic format
│   │   ├── Handle tool_use blocks
│   │   └── Build tool_result content
│   │
│   ├── 1.2.3 Google (Gemini)
│   │   ├── Convert tools to Gemini format
│   │   ├── Handle function_call response
│   │   └── Build function_response
│   │
│   ├── 1.2.4 Universal interface
│   │   ├── ToolCall abstraction (name, arguments, id)
│   │   ├── ToolResult abstraction (id, content)
│   │   └── Converters per provider
│   │
│   ├── Files:
│   │   └── bot/llm.py [EXTENSION]
│   │
│   ├── Dependencies: None
│   │
│   └── Done when:
│       └── Tool-calling works for OpenAI, Anthropic, Google
```

---

## 2. PLUGIN SYSTEM — NEW

```
2. PLUGIN SYSTEM
│
├── 2.1 Tool Registry [NEW]
│   │
│   ├── 2.1.1 Data structures
│   │   ├── ToolDefinition (name, description, parameters, handler, timeout)
│   │   ├── PluginManifest (id, name, version, tools, settings)
│   │   └── ToolStatus (enabled, needs_config, error)
│   │
│   ├── 2.1.2 In-memory storage
│   │   ├── Dict[tool_name, ToolDefinition]
│   │   ├── Dict[plugin_id, PluginManifest]
│   │   └── Sync with DB (statuses, settings)
│   │
│   ├── 2.1.3 API for LLM Router
│   │   ├── get_enabled_tools() → List[ToolDefinition]
│   │   ├── get_tools_for_llm() → List[dict] (OpenAI format)
│   │   └── get_tool(name) → ToolDefinition | None
│   │
│   ├── 2.1.4 Management API
│   │   ├── enable_tool(name)
│   │   ├── disable_tool(name)
│   │   ├── get_tool_status(name) → ToolStatus
│   │   └── list_all_tools() → List[ToolDefinition]
│   │
│   ├── Files:
│   │   ├── tools/__init__.py
│   │   ├── tools/registry.py [NEW]
│   │   └── tools/models.py [NEW]
│   │
│   ├── Dependencies: Plugin Loader
│   │
│   └── Done when:
│       └── Registry stores tools and builds list for LLM
│
├── 2.2 Plugin Loader [NEW]
│   │
│   ├── 2.2.1 Scanning
│   │   ├── Walk plugins/ directory
│   │   ├── Find plugin.yaml in each subfolder
│   │   └── Filter (ignore __pycache__, .git, etc.)
│   │
│   ├── 2.2.2 Manifest parsing
│   │   ├── Read plugin.yaml (PyYAML)
│   │   ├── Schema validation (Pydantic)
│   │   ├── Check required fields
│   │   └── Parse error handling
│   │
│   ├── 2.2.3 Code loading
│   │   ├── importlib.util for handlers.py
│   │   ├── Get handler functions
│   │   ├── Function signature validation
│   │   └── Import error handling
│   │
│   ├── 2.2.4 Registration
│   │   ├── Create ToolDefinition per tool
│   │   ├── Register in Registry
│   │   └── Log loaded plugins
│   │
│   ├── 2.2.5 Hot-reload
│   │   ├── reload_plugin(plugin_id)
│   │   ├── reload_all_plugins()
│   │   ├── Remove old tools from Registry
│   │   └── Load updated ones
│   │
│   ├── Files:
│   │   └── tools/loader.py [NEW]
│   │
│   ├── Dependencies: None
│   │
│   └── Done when:
│       └── Plugins load from folder on startup and on command
│
├── 2.3 Tool Executor [NEW]
│   │
│   ├── 2.3.1 Routing
│   │   ├── Get handler from Registry by name
│   │   ├── Check that tool is enabled
│   │   └── Check that settings are filled
│   │
│   ├── 2.3.2 Execution
│   │   ├── Parse arguments (JSON → dict)
│   │   ├── Call async handler(**kwargs)
│   │   ├── Serialize result (dict/str → str)
│   │   └── Handle return value
│   │
│   ├── 2.3.3 Timeouts
│   │   ├── asyncio.wait_for with timeout from ToolDefinition
│   │   ├── Default timeout (30 sec)
│   │   └── Handle asyncio.TimeoutError
│   │
│   ├── 2.3.4 Error handling
│   │   ├── Tool not found → ToolNotFoundError
│   │   ├── Tool disabled → ToolDisabledError
│   │   ├── Execution error → ToolExecutionError
│   │   └── Build error message for LLM
│   │
│   ├── 2.3.5 Logging
│   │   ├── Log: tool_name, params, duration, result/error
│   │   ├── Optional: write to tool_call_log (DB)
│   │   └── Metrics (call counters)
│   │
│   ├── Files:
│   │   └── tools/executor.py [NEW]
│   │
│   ├── Dependencies: Tool Registry
│   │
│   └── Done when:
│       └── Executor calls handlers and returns result
│
├── 2.4 Plugin Settings Manager [NEW]
│   │
│   ├── 2.4.1 Read settings
│   │   ├── get_plugin_settings(plugin_id) → dict
│   │   ├── get_setting(plugin_id, key) → any
│   │   └── Decrypt secrets (Fernet)
│   │
│   ├── 2.4.2 Write settings
│   │   ├── save_plugin_settings(plugin_id, settings: dict)
│   │   ├── Validate against plugin.yaml schema
│   │   ├── Encrypt secrets (type: password)
│   │   └── Update status (needs_config → enabled)
│   │
│   ├── 2.4.3 Validation
│   │   ├── Check required fields
│   │   ├── Check types
│   │   ├── Check options for select
│   │   └── Return validation errors
│   │
│   ├── 2.4.4 Configuration status
│   │   ├── is_configured(plugin_id) → bool
│   │   ├── get_missing_settings(plugin_id) → List[str]
│   │   └── Auto-detect needs_config
│   │
│   ├── Files:
│   │   └── tools/settings_manager.py [NEW]
│   │
│   ├── Dependencies: Tools Repository, Encryption
│   │
│   └── Done when:
│       └── Plugin settings read/written with encryption
│
├── 2.5 Plugin Base (utilities for plugins) [NEW]
│   │
│   ├── 2.5.1 Access to settings
│   │   ├── get_setting(key) — for use in handlers
│   │   └── require_setting(key) — raise if missing
│   │
│   ├── 2.5.2 Access to LLM (for plugins with uses_llm)
│   │   ├── get_llm_client() → LLMClient
│   │   ├── generate(prompt) → str
│   │   └── Use main LLM or separate one
│   │
│   ├── 2.5.3 HTTP client
│   │   ├── get_http_client() → httpx.AsyncClient
│   │   └── Preconfigured with timeouts
│   │
│   ├── 2.5.4 Logging
│   │   ├── get_logger(plugin_id) → Logger
│   │   └── Prefix [plugin_id] in logs
│   │
│   ├── Files:
│   │   └── tools/base.py [NEW]
│   │
│   ├── Dependencies: Settings Manager, LLM Engine
│   │
│   └── Done when:
│       └── Plugins can use utilities via import
```

---

## 3. STORAGE — EXTENSION

```
3. STORAGE
│
├── 3.1 Data models [NEW]
│   │
│   ├── 3.1.1 ToolSettingsModel
│   │   ├── tool_name: str (PK)
│   │   ├── plugin_id: str
│   │   ├── enabled: bool (default False)
│   │   ├── settings_json: str (encrypted JSON)
│   │   ├── created_at: datetime
│   │   └── updated_at: datetime
│   │
│   ├── 3.1.2 ToolCallLogModel (optional)
│   │   ├── id: int (PK, autoincrement)
│   │   ├── tool_name: str
│   │   ├── user_id: str (telegram user id)
│   │   ├── chat_id: str
│   │   ├── params_json: str
│   │   ├── result_json: str
│   │   ├── success: bool
│   │   ├── duration_ms: int
│   │   └── created_at: datetime
│   │
│   ├── Files:
│   │   └── api/db.py [EXTENSION]
│   │
│   ├── Dependencies: SQLAlchemy
│   │
│   └── Done when:
│       └── Tables created on startup, migration does not break existing
│
├── 3.2 Tools Repository [NEW]
│   │
│   ├── 3.2.1 CRUD operations
│   │   ├── get_tool_settings(tool_name) → ToolSettingsModel | None
│   │   ├── get_all_tool_settings() → List[ToolSettingsModel]
│   │   ├── save_tool_settings(tool_name, plugin_id, enabled, settings)
│   │   ├── update_tool_enabled(tool_name, enabled)
│   │   └── delete_tool_settings(tool_name)
│   │
│   ├── 3.2.2 Encryption
│   │   ├── encrypt_settings(settings: dict) → str
│   │   ├── decrypt_settings(encrypted: str) → dict
│   │   └── Use existing encryption.py
│   │
│   ├── 3.2.3 Masking for API
│   │   ├── mask_settings(settings: dict, schema: List) → dict
│   │   ├── Mask fields type: password
│   │   └── Format: "***{last_5_chars}"
│   │
│   ├── Files:
│   │   └── api/tools_repository.py [NEW]
│   │
│   ├── Dependencies: db.py, encryption.py
│   │
│   └── Done when:
│       └── CRUD works, secrets encrypted like TG/LLM
```

---

## 4. ADMIN API — EXTENSION

```
4. ADMIN API
│
├── 4.1 Tools Router [NEW]
│   │
│   ├── 4.1.1 GET /api/tools
│   │   ├── List all tools
│   │   ├── Data from Registry + statuses from DB
│   │   ├── Response: [{name, description, plugin_id, enabled, needs_config}]
│   │   └── Auth: X-Admin-Key
│   │
│   ├── 4.1.2 GET /api/tools/{name}
│   │   ├── Tool details
│   │   ├── Includes: description, parameters, settings schema
│   │   ├── Response: {name, description, parameters, settings_schema, current_settings (masked)}
│   │   └── 404 if not found
│   │
│   ├── 4.1.3 POST /api/tools/{name}/enable
│   │   ├── Enable tool
│   │   ├── Check: settings filled (if required)
│   │   ├── Response: {success, message}
│   │   └── 400 if needs_config
│   │
│   ├── 4.1.4 POST /api/tools/{name}/disable
│   │   ├── Disable tool
│   │   ├── Response: {success}
│   │   └── Always success
│   │
│   ├── 4.1.5 GET /api/tools/{name}/settings
│   │   ├── Get settings (masked)
│   │   ├── Response: {settings: {...}, schema: [...]}
│   │   └── Passwords masked
│   │
│   ├── 4.1.6 PUT /api/tools/{name}/settings
│   │   ├── Save settings
│   │   ├── Body: {settings: {...}}
│   │   ├── Schema validation
│   │   ├── Response: {success, errors?}
│   │   └── 400 on validation errors
│   │
│   ├── 4.1.7 POST /api/tools/{name}/test
│   │   ├── Test connection (if external API exists)
│   │   ├── Call special test handler (optional)
│   │   ├── Response: {success, message, details?}
│   │   └── 400/500 on error
│   │
│   ├── Files:
│   │   └── api/tools_router.py [NEW]
│   │
│   ├── Dependencies: Tool Registry, Tools Repository, Settings Manager
│   │
│   └── Done when:
│       └── All endpoints work, Swagger docs
│
├── 4.2 Plugins Router [NEW]
│   │
│   ├── 4.2.1 POST /api/plugins/reload
│   │   ├── Reload all plugins
│   │   ├── Call Plugin Loader.reload_all()
│   │   ├── Response: {success, loaded: [...], errors: [...]}
│   │   └── Partial success possible
│   │
│   ├── 4.2.2 POST /api/plugins/{id}/reload
│   │   ├── Reload specific plugin
│   │   ├── Response: {success, message}
│   │   └── 404 if not found
│   │
│   ├── 4.2.3 GET /api/plugins
│   │   ├── List plugins
│   │   ├── Response: [{id, name, version, tools_count, enabled_count}]
│   │   └── Group by plugin
│   │
│   ├── Files:
│   │   └── api/plugins_router.py [NEW]
│   │
│   ├── Dependencies: Plugin Loader
│   │
│   └── Done when:
│       └── Hot-reload works via API
│
├── 4.3 Integration in app.py [EXTENSION]
│   │
│   ├── 4.3.1 Mount routers
│   │   ├── app.include_router(tools_router)
│   │   └── app.include_router(plugins_router)
│   │
│   ├── 4.3.2 Startup event
│   │   ├── Initialize Plugin Loader
│   │   ├── Load plugins
│   │   └── Sync Registry with DB
│   │
│   ├── Files:
│   │   └── api/app.py [EXTENSION]
│   │
│   └── Done when:
│       └── Plugins load on application startup
```

---

## 5. ADMIN PANEL (UI) — EXTENSION

```
5. ADMIN PANEL
│
├── 5.1 Navigation [EXTENSION]
│   │
│   ├── 5.1.1 Menu structure
│   │   ├── Settings (existing)
│   │   ├── Tools (new)
│   │   └── Administrators (new)
│   │
│   ├── 5.1.2 Routing
│   │   ├── #settings (existing)
│   │   ├── #tools (new)
│   │   └── #admins (new)
│   │
│   ├── 5.1.3 Active menu item
│   │   └── Highlight current section
│   │
│   ├── Files:
│   │   ├── admin/index.html [EXTENSION]
│   │   └── admin/app.js [EXTENSION]
│   │
│   └── Done when:
│       └── Menu with 3 items, section switching
│
├── 5.2 "Tools" page [NEW]
│   │
│   ├── 5.2.1 Tool list
│   │   ├── Load GET /api/tools
│   │   ├── Display cards/table
│   │   ├── Group by plugin (optional)
│   │   └── Filter: all / enabled / disabled
│   │
│   ├── 5.2.2 Tool card
│   │   ├── Name
│   │   ├── Description
│   │   ├── Plugin (source)
│   │   ├── Status (badge): Enabled / Disabled / Needs config
│   │   └── Action buttons
│   │
│   ├── 5.2.3 Tool actions
│   │   ├── "Enable" button → POST /api/tools/{name}/enable
│   │   ├── "Disable" button → POST /api/tools/{name}/disable
│   │   ├── "Settings" button → open modal/page
│   │   └── Toast on success/error
│   │
│   ├── 5.2.4 Tool settings form
│   │   ├── Header with tool name
│   │   ├── Dynamic form from settings schema
│   │   ├── Field types: text, password, number, select, checkbox
│   │   ├── Password masking (show/hide)
│   │   ├── Client-side validation
│   │   ├── "Test connection" button (if test exists)
│   │   └── Buttons: Save, Cancel
│   │
│   ├── 5.2.5 "Reload plugins" button
│   │   ├── POST /api/plugins/reload
│   │   ├── Loading indicator
│   │   └── Toast with result
│   │
│   ├── Files:
│   │   ├── admin/index.html [EXTENSION] or admin/tools.html [NEW]
│   │   ├── admin/tools.js [NEW]
│   │   └── admin/styles.css [EXTENSION]
│   │
│   ├── Dependencies: Tools API ready
│   │
│   └── Done when:
│       └── Full tool management via UI
│
├── 5.3 "Administrators" page [NEW]
│   │
│   ├── 5.3.1 Administrator list
│   │   ├── Load GET /api/service-admins
│   │   ├── Table: ID, Name, Username, Date added
│   │   └── Empty state: "No administrators"
│   │
│   ├── 5.3.2 Add administrator
│   │   ├── "+ Add" button
│   │   ├── Modal with form
│   │   ├── Field: Telegram ID (number, required)
│   │   ├── Hint about @userinfobot
│   │   ├── POST /api/service-admins
│   │   └── Toast with result
│   │
│   ├── 5.3.3 Administrator actions
│   │   ├── "Refresh" button → POST /api/service-admins/{id}/refresh
│   │   ├── "Remove" button → confirmation modal
│   │   └── DELETE /api/service-admins/{id}
│   │
│   ├── 5.3.4 Delete confirmation modal
│   │   ├── Text: "Remove administrator {name}?"
│   │   └── Buttons: Remove (danger), Cancel
│   │
│   ├── Files:
│   │   ├── admin/index.html [EXTENSION] or admin/admins.html [NEW]
│   │   ├── admin/admins.js [NEW]
│   │   └── admin/styles.css [EXTENSION]
│   │
│   ├── Dependencies: API already exists!
│   │
│   └── Done when:
│       └── Full admin management via UI
```

---

## 6. BUILTIN PLUGINS — NEW

```
6. BUILTIN PLUGINS
│
├── 6.1 Calculator [NEW]
│   │
│   ├── 6.1.1 plugin.yaml
│   │   ├── id: calculator
│   │   ├── name: "Calculator"
│   │   ├── version: "1.0.0"
│   │   ├── enabled: true (default)
│   │   └── tools:
│   │       └── calculate
│   │           ├── description: "Evaluates mathematical expression"
│   │           └── parameters: {expression: string}
│   │
│   ├── 6.1.2 handlers.py
│   │   ├── async def calculate(expression: str) → str
│   │   ├── Safe eval (no __builtins__)
│   │   ├── Support: +, -, *, /, **, sqrt, sin, cos, etc.
│   │   └── Error handling (division by zero, syntax)
│   │
│   ├── Files:
│   │   ├── plugins/builtin/calculator/plugin.yaml
│   │   └── plugins/builtin/calculator/handlers.py
│   │
│   ├── Settings: None
│   │
│   └── Done when:
│       └── "Calculate 2+2*3" → "8"
│
├── 6.2 DateTime Tools [NEW]
│   │
│   ├── 6.2.1 plugin.yaml
│   │   ├── id: datetime-tools
│   │   ├── name: "Date & Time"
│   │   ├── version: "1.0.0"
│   │   ├── enabled: true
│   │   └── tools:
│   │       ├── get_current_datetime
│   │       │   └── description: "Returns current date and time"
│   │       └── get_weekday
│   │           ├── description: "Returns weekday for a date"
│   │           └── parameters: {date: string}
│   │
│   ├── 6.2.2 handlers.py
│   │   ├── async def get_current_datetime() → str
│   │   │   └── Return: "2024-01-15 14:30:00 (Monday)"
│   │   └── async def get_weekday(date: str) → str
│   │       ├── Date parsing (various formats)
│   │       └── Return: "Monday" or localized weekday
│   │
│   ├── Files:
│   │   ├── plugins/builtin/datetime_tools/plugin.yaml
│   │   └── plugins/builtin/datetime_tools/handlers.py
│   │
│   ├── Settings:
│   │   └── timezone (optional, default: UTC)
│   │
│   └── Done when:
│       └── "What time is it?" → current time
```

---

## 7. BUSINESS PLUGINS — NEW (Phase 6+)

```
7. BUSINESS PLUGINS
│
├── 7.1 Worklog Checker [PHASE 6]
│   │
│   ├── 7.1.1 plugin.yaml
│   │   ├── id: worklog-checker
│   │   ├── name: "Worklog checker"
│   │   ├── version: "1.0.0"
│   │   ├── enabled: false (requires config)
│   │   ├── tools:
│   │   │   ├── check_worklogs
│   │   │   │   ├── description: "Checks employee worklogs..."
│   │   │   │   ├── parameters: {employee: string, period: string}
│   │   │   │   └── timeout: 60
│   │   │   └── get_worklog_summary
│   │   │       ├── description: "Gets team worklog summary"
│   │   │       └── parameters: {team: string, period: string}
│   │   └── settings:
│   │       ├── jira_url (string, required)
│   │       ├── jira_email (string, required)
│   │       ├── jira_token (password, required)
│   │       ├── tempo_token (password, required)
│   │       ├── required_hours_per_day (number, default: 8)
│   │       └── working_days (string, default: "mon,tue,wed,thu,fri")
│   │
│   ├── 7.1.2 handlers.py
│   │   ├── async def check_worklogs(employee, period) → dict
│   │   │   ├── Get settings
│   │   │   ├── Find employee in Jira
│   │   │   ├── Fetch worklogs from Tempo
│   │   │   ├── Compute required hours and deficit
│   │   │   └── Return: {employee, period, logged, required, deficit, tasks}
│   │   └── async def get_worklog_summary(team, period) → dict
│   │
│   ├── 7.1.3 jira_client.py (helper)
│   │   ├── class JiraClient
│   │   ├── search_user(query) → User
│   │   ├── get_issues(user, period) → List[Issue]
│   │   └── API error handling
│   │
│   ├── 7.1.4 tempo_client.py (helper)
│   │   ├── class TempoClient
│   │   ├── get_worklogs(user_key, date_from, date_to) → List[Worklog]
│   │   └── API error handling
│   │
│   ├── 7.1.5 test handler (optional)
│   │   ├── async def test_connection() → dict
│   │   ├── Test Jira connection
│   │   ├── Test Tempo connection
│   │   └── Return: {jira_ok, tempo_ok, errors}
│   │
│   ├── Files:
│   │   ├── plugins/worklog_checker/plugin.yaml
│   │   ├── plugins/worklog_checker/handlers.py
│   │   ├── plugins/worklog_checker/jira_client.py
│   │   └── plugins/worklog_checker/tempo_client.py
│   │
│   ├── Dependencies: httpx, Jira API, Tempo API
│   │
│   └── Done when:
│       └── "Check Ivanov's worklogs" → real data
│
├── 7.2 HR Service [SPEC: SPEC_HR_SERVICE.md]
│   │
│   ├── План с чекбоксами для отметки выполнения: [PLAN_HR_SERVICE.md](PLAN_HR_SERVICE.md)
│   │
│   ├── 7.2.1 Functions (функции плагина; плагин = один инструмент для оркестратора)
│   │   ├── get_employee — get employee data (by ФИО, personal_number, email)
│   │   ├── list_employees — list with filters (МВЗ, команда, руководители, delivery managers)
│   │   ├── search_employees — search by name/department/position
│   │   ├── update_employee — update data (только сервисные админы в боте)
│   │   └── import_employees — import from Excel (два листа ДДЖ + Инфоком)
│   │
│   ├── 7.2.2 Storage
│   │   ├── Отдельная таблица employees (или hr_employees) в той же SQLite
│   │   ├── Индексы: personal_number (unique), email, jira_worker_id
│   │   └── Миграция или создание при первом обращении
│   │
│   ├── 7.2.3 Import
│   │   ├── Парсинг .xlsx/.xls, листы «ДДЖ» и «Инфоком», маппинг по SPEC
│   │   ├── Проверка дубликатов personal_number в файле → ошибка с расшифровкой
│   │   ├── Сверка с БД: существующие пропуск, новые — вставка
│   │   └── Дообогащение jira_worker_id из Jira (GET /rest/api/2/user?username=…)
│   │
│   ├── 7.2.4 Bot & Admin
│   │   ├── Передача файла из бота в плагин (import_employees); проверка service_admins
│   │   ├── API для админки: GET/PATCH /api/hr/employees, POST /api/hr/import
│   │   └── Админка «Работа с БД» (/admin/#db): три представления, таблица, импорт
│   │
│   └── Done when:
│       └── Импорт (бот + админка) работает, дообогащение Jira, правки через бота и админку, права соблюдаются
│
├── 7.3 Reminder [FUTURE]
│   │
│   ├── 7.3.1 Functions (функции плагина; плагин = один инструмент для оркестратора)
│   │   ├── find_violators — find violators for period
│   │   ├── send_reminder — send reminder (uses_llm: true)
│   │   └── escalate_to_manager — escalate to manager
│   │
│   ├── 7.3.2 LLM integration
│   │   ├── Generate personalized text
│   │   ├── Configurable tone (friendly/formal/strict)
│   │   └── Prompts in templates.py
│   │
│   ├── 7.3.3 Scheduler integration
│   │   ├── Cron job: check violators
│   │   ├── Auto-send reminders
│   │   └── Escalation on timeout
│   │
│   └── Done when:
│       └── Automated reminders with personalization
```

---

## Summary table of all components

| # | Block | Subblock | Type | Phase | Files |
|---|-------|----------|------|-------|-------|
| 1.1 | LLM Engine | LLM Router | New | 1 | bot/tool_calling.py |
| 1.2 | LLM Engine | Provider Adapter | Extension | 1 | bot/llm.py |
| 2.1 | Plugin System | Tool Registry | New | 2 | tools/registry.py, models.py |
| 2.2 | Plugin System | Plugin Loader | New | 2 | tools/loader.py |
| 2.3 | Plugin System | Tool Executor | New | 2 | tools/executor.py |
| 2.4 | Plugin System | Settings Manager | New | 3 | tools/settings_manager.py |
| 2.5 | Plugin System | Plugin Base | New | 2 | tools/base.py |
| 3.1 | Storage | Data models | New | 3 | api/db.py |
| 3.2 | Storage | Tools Repository | New | 3 | api/tools_repository.py |
| 4.1 | Admin API | Tools Router | New | 3 | api/tools_router.py |
| 4.2 | Admin API | Plugins Router | New | 3 | api/plugins_router.py |
| 4.3 | Admin API | Integration | Extension | 3 | api/app.py |
| 5.1 | Admin Panel | Navigation | Extension | 4 | admin/index.html, app.js |
| 5.2 | Admin Panel | Tools | New | 4 | admin/tools.js |
| 5.3 | Admin Panel | Administrators | New | 5 | admin/admins.js |
| 6.1 | Builtin Plugins | Calculator | New | 2 | plugins/builtin/calculator/* |
| 6.2 | Builtin Plugins | DateTime | New | 2 | plugins/builtin/datetime_tools/* |
| 7.1 | Business Plugins | Worklog Checker | New | 6 | plugins/worklog_checker/* |
| 7.2 | Business Plugins | HR Service | New | 7+ | plugins/hr_service/* |
| 7.3 | Business Plugins | Reminder | New | 7+ | plugins/reminder/* |

---

## Phase breakdown

### Phase 0: Stabilization (1–2 days)
- [ ] Review current tests
- [ ] Tag working state
- [ ] Create branch for work

### Phase 1: Tool-calling in LLM (3–5 days)
- [ ] 1.1 LLM Router
- [ ] 1.2 LLM Provider Adapter (extension)
- [ ] Tool-calling tests

### Phase 2: Plugin System (5–7 days)
- [ ] 2.1 Tool Registry
- [ ] 2.2 Plugin Loader
- [ ] 2.3 Tool Executor
- [ ] 2.5 Plugin Base
- [ ] 6.1 Calculator plugin
- [ ] 6.2 DateTime plugin
- [ ] Plugin system tests

### Phase 3: Storage + API (3–5 days)
- [ ] 3.1 Data models
- [ ] 3.2 Tools Repository
- [ ] 2.4 Settings Manager
- [ ] 4.1 Tools Router
- [ ] 4.2 Plugins Router
- [ ] 4.3 Integration in app.py
- [ ] API tests

### Phase 4: Admin "Tools" (5–7 days)
- [ ] 5.1 Navigation (extension)
- [ ] 5.2 "Tools" page
- [ ] Manual UI testing

### Phase 5: Admin "Administrators" (3–5 days)
- [ ] 5.3 "Administrators" page
- [ ] Manual UI testing

**Note:** Phase 5 can run in parallel with Phases 3–4

### Phase 6: Worklog Checker (1–2 weeks)
- [ ] 7.1 Worklog Checker plugin
- [ ] Jira API integration
- [ ] Tempo API integration
- [ ] E2E testing

### Phase 7+: Future plugins
- [ ] 7.2 HR Service
- [ ] 7.3 Reminder
- [ ] Others as needed

---

## Effort estimate

| Phase | Description | Estimate |
|-------|-------------|----------|
| 0 | Stabilization | 1–2 days |
| 1 | Tool-calling | 3–5 days |
| 2 | Plugin System | 5–7 days |
| 3 | Storage + API | 3–5 days |
| 4 | Admin "Tools" | 5–7 days |
| 5 | Admin "Administrators" | 3–5 days |
| 6 | Worklog Checker | 1–2 weeks |
| **Total to MVP** | Phases 0–6 | **6–8 weeks** |

---

## Document versioning

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-02-06 | First version of task breakdown |
