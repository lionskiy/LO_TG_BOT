# ARCHITECTURE BLUEPRINT — LO_TG_BOT

> **Primary architecture document for development**  
> Used as a reference when working on each block/phase

**Version:** 1.2  
**Date:** 2026-02-07  
**Approach:** Smart monolith with plugins (single process)

---

## Related documents

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target architecture (this document) | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Task breakdown to 3–4 levels | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Detailed plan for Phase 0–1 | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Detailed plan for Phase 2 (Plugin System) | ✅ Current (in progress) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Detailed plan for Phase 3 (Storage + API) | ✅ Current (in progress) |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Detailed plan for Phase 4 (Admin Tools) | ✅ Current (in progress) |
| [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Detailed plan for Phase 5 (Admin Administrators) | ✅ Current (in progress) |
| [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Detailed plan for Phase 6 (Worklog Checker) | ✅ Current (in progress) |

### Current state (v1.0) — implemented

| Document | Description |
|----------|-------------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Full specification of current implementation: architecture, API, installation |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

Phase plans (0–6) build on this base and add tool-calling, plugins, tools/administrators admin UI, and Worklog Checker.

---

## How to use this document

1. **When starting work on a block** — refer to the "Blocks for independent development" section
2. **When creating a plugin** — follow the standard in the "Plugin structure" section
3. **For flow questions** — see the "Request processing flow" section
4. **For optimization** — consider the "Resources and constraints" section
5. **When planning work** — see [UPGRADE_TASKS.md](UPGRADE_TASKS.md)
6. **When implementing a specific phase** — see the corresponding PLAN_PHASE_X.md

---

## Terminology (единая терминология во всех документах)

- **Плагин = инструмент для оркестратора.** Для оркестратора (LLM и бот) каждый плагин выступает как **один инструмент**: один пункт в списке вызовов; оркестратор вызывает плагин с параметрами (действие + аргументы).
- **У плагина не инструменты, а функции.** Внутри плагина реализованы **функции** (например, get_employee, check_worklogs, import_employees), которые выполняют конкретные операции. Снаружи они не разбиваются на отдельные «инструменты» оркестратора — с точки зрения оркестратора вызывается один инструмент (плагин), который сам выбирает и выполняет нужную функцию по параметрам.

В коде и API могут сохраняться технические имена (tool_name, Tool Registry, tools в plugin.yaml) для совместимости с LLM API; в описаниях и спецификациях везде используем: **плагин = инструмент оркестратора**, **функции плагина** = внутренние операции плагина.

---

## 1. High-level diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                        LO_TG_BOT (Single Python process)                         │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                            │ │
│  │                    ENTRY POINT (Telegram Bot)                              │ │
│  │                                                                            │ │
│  │   • Long polling (python-telegram-bot)                                     │ │
│  │   • Receiving messages from users                                          │ │
│  │   • Sending replies                                                        │ │
│  │   • Single instance (.bot.pid)                                             │ │
│  │   • Subprocess managed via bot_runner                                      │ │
│  │                                                                            │ │
│  │   [NO CHANGES — block stable]                                              │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                            │ │
│  │                      ORCHESTRATOR (LLM Engine)                             │ │
│  │                                                                            │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │   │  Conversation Manager                                             │    │ │
│  │   │  • Conversation history (20 user/assistant pairs)                 │    │ │
│  │   │  • Context by chat_id                                             │    │ │
│  │   │  [ALREADY in telegram_bot.py]                                     │    │ │
│  │   └──────────────────────────────────────────────────────────────────┘    │ │
│  │                                        │                                   │ │
│  │                                        ▼                                   │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │   │  LLM Router                                               [NEW]   │    │ │
│  │   │                                                                   │    │ │
│  │   │  • Builds request: system_prompt + tools + history + message     │    │ │
│  │   │  • System prompt in English (token savings)                      │    │ │
│  │   │  • Plugin (as tool) descriptions from Registry                               │    │ │
│  │   │  • Sends to LLM Provider                                          │    │ │
│  │   │  • Handles tool_calls                                             │    │ │
│  │   │  • Returns final reply in user language                           │    │ │
│  │   └──────────────────────────────────────────────────────────────────┘    │ │
│  │                                        │                                   │ │
│  │                                        ▼                                   │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │   │  LLM Provider Adapter                                             │    │ │
│  │   │                                                                   │    │ │
│  │   │  • OpenAI (GPT-4o-mini, GPT-4o)        ✅ tool-calling            │    │ │
│  │   │  • Anthropic (Claude)                  ✅ tool-calling            │    │ │
│  │   │  • Google (Gemini)                     ✅ tool-calling            │    │ │
│  │   │  • Groq, OpenRouter, Ollama            ⚠️ basic tool-calling     │    │ │
│  │   │  • Azure, YandexGPT, etc.              ⚠️ model-dependent          │    │ │
│  │   │                                                                   │    │ │
│  │   │  [EXTENSION of existing bot/llm.py]                               │    │ │
│  │   └──────────────────────────────────────────────────────────────────┘    │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                          ┌─────────────┴─────────────┐                          │
│                          ▼                           ▼                          │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │                                 │  │                                     │  │
│  │     TOOL REGISTRY     [NEW]     │  │    TOOL EXECUTOR          [NEW]     │  │
│  │                                 │  │                                     │  │
│  │  • List of tools                │  │  • Call routing                     │  │
│  │  • Descriptions (English)       │  │  • Invoke plugin handler            │  │
│  │  • Parameters (JSON Schema)      │  │  • Error handling                  │  │
│  │  • Status (enabled/disabled)    │  │  • Timeouts                         │  │
│  │  • Build tools for LLM          │  │  • Call logging                     │  │
│  │                                 │  │                                     │  │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘  │
│                 ▲                                      │                        │
│                 │                                      ▼                        │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                            │ │
│  │                         PLUGIN SYSTEM                            [NEW]      │ │
│  │                                                                            │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │   │  Plugin Loader                                                    │    │ │
│  │   │                                                                   │    │ │
│  │   │  • Scans plugins/ directory                                       │    │ │
│  │   │  • Reads plugin.yaml (manifests)                                  │    │ │
│  │   │  • Loads handlers.py (code)                                       │    │ │
│  │   │   │  • Registers each plugin as one tool; plugin exposes functions  │    │ │
│  │   │  • Hot-reload plugins (no restart)                                 │    │ │
│  │   └──────────────────────────────────────────────────────────────────┘    │ │
│  │                                        │                                   │ │
│  │                                        ▼                                   │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │   │  Plugin Settings Manager                                          │    │ │
│  │   │                                                                   │    │ │
│  │   │  • Read/write plugin settings from DB                             │    │ │
│  │   │  • Secret encryption (Fernet)                                    │    │ │
│  │   │  • Validation against plugin.yaml schema                         │    │ │
│  │   └──────────────────────────────────────────────────────────────────┘    │ │
│  │                                        │                                   │ │
│  │                                        ▼                                   │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │   │  Plugin LLM Client (optional)                                      │    │ │
│  │   │                                                                   │    │ │
│  │   │  • Shared client for plugins that need LLM                        │    │ │
│  │   │  • Can use main LLM or separate one                               │    │ │
│  │   │  • Per-plugin prompts                                              │    │ │
│  │   └──────────────────────────────────────────────────────────────────┘    │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                            │ │
│  │                              PLUGINS                                       │ │
│  │                                                                            │ │
│  │   plugins/                                                                 │ │
│  │   │                                                                        │ │
│  │   ├── builtin/                          [NEW — with core]                  │ │
│  │   │   ├── calculator/                                                      │ │
│  │   │   │   ├── plugin.yaml               # plugin (tool) + functions         │ │
│  │   │   │   └── handlers.py               # functions: calculate()            │ │
│  │   │   │                                                                    │ │
│  │   │   └── datetime_tools/                                                  │ │
│  │   │       ├── plugin.yaml                                                  │ │
│  │   │       └── handlers.py               # functions: get_datetime(), get_weekday() │ │
│  │   │                                                                        │ │
│  │   ├── worklog_checker/                  [PHASE 6 — first business plugin] │ │
│  │   │   ├── plugin.yaml                   # functions + settings (jira, tempo)   │ │
│  │   │   └── handlers.py                   # functions: check_worklogs()                 │ │
│  │   │                                                                        │ │
│  │   ├── hr_service/                       [FUTURE]                           │ │
│  │   │   ├── plugin.yaml                                                      │ │
│  │   │   └── handlers.py                   # get_employee(), update_employee()│ │
│  │   │                                                                        │ │
│  │   ├── reminder/                         [FUTURE — uses LLM]                │ │
│  │   │   ├── plugin.yaml                   # uses_llm: true                   │ │
│  │   │   └── handlers.py                   # send_reminder() → LLM generation │ │
│  │   │                                                                        │ │
│  │   └── (other plugins...)                                                   │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                            │ │
│  │                            ADMIN API (FastAPI)                             │ │
│  │                                                                            │ │
│  │   Existing endpoints [NO CHANGES]:                                         │ │
│  │   ├── /api/settings/telegram/*          # CRUD + test + activate          │ │
│  │   ├── /api/settings/llm/*               # CRUD + test + activate          │ │
│  │   └── /api/service-admins/*             # CRUD administrators                │ │
│  │                                                                            │ │
│  │   New endpoints [NEW]:                                                    │ │
│  │   ├── /api/tools                        # GET list of tools                 │ │
│  │   ├── /api/tools/{name}                 # GET tool details                  │ │
│  │   ├── /api/tools/{name}/enable          # POST enable                       │ │
│  │   ├── /api/tools/{name}/disable         # POST disable                      │ │
│  │   ├── /api/tools/{name}/settings        # GET/PUT settings                  │ │
│  │   ├── /api/tools/{name}/test            # POST test (if available)          │ │
│  │   └── /api/plugins/reload               # POST reload plugins               │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                            │ │
│  │                          ADMIN PANEL (Static)                             │ │
│  │                                                                            │ │
│  │   Menu:                                                                   │ │
│  │   │                                                                        │ │
│  │   ├── Settings                          [NO CHANGES]                       │ │
│  │   │   ├── "Telegram bot" block                                             │ │
│  │   │   └── "LLM" block                                                      │ │
│  │   │                                                                        │ │
│  │   ├── Tools                             [NEW — Phase 4]                    │ │
│  │   │   ├── List of tools                                                    │ │
│  │   │   ├── Enable/disable                                                   │ │
│  │   │   ├── Tool settings                                                    │ │
│  │   │   └── Connection test                                                  │ │
│  │   │                                                                        │ │
│  │   └── Administrators                   [NEW — Phase 5]                    │ │
│  │       ├── List of admins                                                   │ │
│  │       ├── Add by Telegram ID                                               │ │
│  │       └── Remove                                                           │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                            │ │
│  │                              STORAGE (SQLite)                              │ │
│  │                                                                            │ │
│  │   Existing tables [NO CHANGES]:                                            │ │
│  │   ├── telegram_settings                 # token, base_url, status          │ │
│  │   ├── llm_settings                      # provider, key, model, prompt     │ │
│  │   └── service_admins                    # telegram_id, profile data       │ │
│  │                                                                            │ │
│  │   New tables [NEW]:                                                       │ │
│  │   ├── tool_settings                     # tool settings                     │ │
│  │   │   ├── tool_name (PK)                                                   │ │
│  │   │   ├── enabled (bool)                                                   │ │
│  │   │   ├── settings_json (encrypted)     # JSON settings                     │ │
│  │   │   └── updated_at                                                       │ │
│  │   │                                                                        │ │
│  │   └── tool_call_log                     # call log (optional)               │ │
│  │       ├── id                                                               │ │
│  │       ├── tool_name                                                        │ │
│  │       ├── user_id                                                          │ │
│  │       ├── params_json                                                      │ │
│  │       ├── result_json                                                      │ │
│  │       ├── duration_ms                                                      │ │
│  │       └── created_at                                                       │ │
│  │                                                                            │ │
│  │   Encryption: Fernet (as now)                                              │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                              EXTERNAL SYSTEMS                                    │
│                                                                                  │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│   │  Telegram API  │  │  LLM Providers │  │  Jira / Tempo  │  │  Mattermost  │  │
│   │                │  │                │  │                │  │  (future)    │  │
│   │  • getUpdates  │  │  • OpenAI      │  │  • REST API    │  │              │  │
│   │  • sendMessage │  │  • Anthropic   │  │  • Worklogs    │  │  • Webhook   │  │
│   │  • getMe       │  │  • Google      │  │  • Issues      │  │  • Messages  │  │
│   │                │  │  • Groq, etc.  │  │                │  │              │  │
│   └────────────────┘  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                                                  │
│   All calls OUTBOUND (application initiates)                                     │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Blocks for independent development

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                        MAP OF INDEPENDENT BLOCKS                                  │
│                                                                                  │
│  ═══════════════════════════════════════════════════════════════════════════    │
│  CORE — done once, then stable                                                   │
│  ═══════════════════════════════════════════════════════════════════════════    │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  BLOCK A: Tool-calling in LLM Engine                      [Phase 1]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • bot/llm.py                    — extend get_reply()                    │   │
│   │  • bot/tool_calling.py           — new, tool-calling logic               │   │
│   │                                                                         │   │
│   │  Dependencies: None (self-contained)                                    │   │
│   │  Tests: tests/test_tool_calling.py                                      │   │
│   │                                                                         │   │
│   │  Done when:                                                             │   │
│   │  • LLM invokes hardcoded tools                                          │   │
│   │  • Regular chat works as before                                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│                                        ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  BLOCK B: Tool Registry + Plugin Loader                    [Phase 2]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • tools/__init__.py                                                    │   │
│   │  • tools/registry.py             — tool registry                        │   │
│   │  • tools/loader.py               — plugin loader                        │   │
│   │  • tools/base.py                 — base utilities for plugins           │   │
│   │                                                                         │   │
│   │  Dependencies: Block A                                                  │   │
│   │  Tests: tests/test_tools_registry.py                                    │   │
│   │                                                                         │   │
│   │  Done when:                                                             │   │
│   │  • Tools load from YAML                                                 │   │
│   │  • Registry builds tools for LLM                                        │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│                                        ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  BLOCK C: Tool settings in DB                             [Phase 3]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • api/db.py                     — add ToolSettingsModel                │   │
│   │  • api/tools_repository.py       — CRUD for settings                     │   │
│   │  • api/tools_router.py           — API endpoints                         │   │
│   │  • api/app.py                    — mount router                          │   │
│   │                                                                         │   │
│   │  Dependencies: Block B                                                  │   │
│   │  Tests: tests/test_tools_api.py                                         │   │
│   │                                                                         │   │
│   │  Done when:                                                             │   │
│   │  • API for managing tools                                               │   │
│   │  • Settings encrypted like TG/LLM                                       │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│                                        ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  BLOCK D: Builtin plugins (calculator, datetime)            [Phase 2]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • plugins/builtin/calculator/plugin.yaml                               │   │
│   │  • plugins/builtin/calculator/handlers.py                               │   │
│   │  • plugins/builtin/datetime_tools/plugin.yaml                           │   │
│   │  • plugins/builtin/datetime_tools/handlers.py                           │   │
│   │                                                                         │   │
│   │  Dependencies: Block B                                                  │   │
│   │  Tests: tests/test_builtin_plugins.py                                   │   │
│   │                                                                         │   │
│   │  Done when:                                                             │   │
│   │  • "What time is it?" → reply via tool                                 │   │
│   │  • "Calculate 2+2*3" → reply via tool                                  │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ═══════════════════════════════════════════════════════════════════════════    │
│  ADMIN UI — independent UI blocks                                                │
│  ═══════════════════════════════════════════════════════════════════════════    │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  BLOCK E: Admin "Tools"                                   [Phase 4]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • admin/index.html              — new menu item                         │   │
│   │  • admin/tools.js                — tools page logic                      │   │
│   │  • admin/styles.css             — styles                                │   │
│   │                                                                         │   │
│   │  Dependencies: Block C (API ready)                                      │   │
│   │  Tests: manual UI testing                                               │   │
│   │                                                                         │   │
│   │  Done when:                                                             │   │
│   │  • Tool list in UI                                                      │   │
│   │  • Enable/disable                                                       │   │
│   │  • Settings form                                                        │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  BLOCK F: Admin "Administrators"                           [Phase 5]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • admin/index.html              — new menu item                         │   │
│   │  • admin/admins.js              — admins page logic                     │   │
│   │                                                                         │   │
│   │  Dependencies: None (API already exists!)                               │   │
│   │  Tests: manual UI testing                                                │   │
│   │                                                                         │   │
│   │  Done when:                                                             │   │
│   │  • Admin list in UI                                                     │   │
│   │  • Add/remove                                                            │   │
│   │                                                                         │   │
│   │  NOTE: Can be done in parallel with other phases!                       │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ═══════════════════════════════════════════════════════════════════════════    │
│  PLUGINS — each developed independently                                         │
│  ═══════════════════════════════════════════════════════════════════════════    │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  PLUGIN: Worklog Checker                                  [Phase 6]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • plugins/worklog_checker/plugin.yaml                                  │   │
│   │  • plugins/worklog_checker/handlers.py                                  │   │
│   │  • plugins/worklog_checker/jira_client.py  (optional)                   │   │
│   │  • plugins/worklog_checker/tempo_client.py (optional)                   │   │
│   │                                                                         │   │
│   │  Dependencies: Core ready (Blocks A–D)                                  │   │
│   │  External APIs: Jira REST API, Tempo API                               │   │
│   │  Settings: jira_url, jira_token, tempo_token                            │   │
│   │                                                                         │   │
│   │  Done when:                                                             │   │
│   │  • "Check Ivanov's worklogs" → real data from Jira                      │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  PLUGIN: HR Service                                       [Future]      │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • plugins/hr_service/plugin.yaml                                       │   │
│   │  • plugins/hr_service/handlers.py                                       │   │
│   │                                                                         │   │
│   │  Functions (функции плагина):                                            │   │
│   │  • get_employee — get employee data                                     │   │
│   │  • list_employees — list employees                                     │   │
│   │  • update_employee — update data                                       │   │
│   │  • import_employees — import from Excel/CSV                             │   │
│   │                                                                         │   │
│   │  Dependencies: Core                                                     │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  PLUGIN: Reminder (with LLM)                               [Future]     │   │
│   │                                                                         │   │
│   │  Files:                                                                 │   │
│   │  • plugins/reminder/plugin.yaml        # uses_llm: true                  │   │
│   │  • plugins/reminder/handlers.py                                         │   │
│   │  • plugins/reminder/templates.py       # prompts for generation          │   │
│   │                                                                         │   │
│   │  Functions (функции плагина):                                            │   │
│   │  • find_violators — find violators                                      │   │
│   │  • send_reminder — generate and send reminder                           │   │
│   │  • escalate — escalate to manager                                       │   │
│   │                                                                         │   │
│   │  Note: Uses LLM for text generation                                     │   │
│   │  Dependencies: Core + worklog_checker + hr_service                      │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  PLUGIN: Calculator (external API example)                 [Future]      │   │
│   │                                                                         │   │
│   │  plugin.yaml:                                                           │   │
│   │    type: external                      # external HTTP endpoint         │   │
│   │    endpoint: http://calc-service:8001                                    │   │
│   │                                                                         │   │
│   │  Shows how to connect an external service                               │   │
│   │  (when moving to corporate environment and scaling is needed)           │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Development order and dependencies

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                         DEPENDENCY GRAPH                                          │
│                                                                                  │
│                                                                                  │
│   ┌─────────────┐                                                                │
│   │  Phase 0    │  Stabilization, tests, branch                                 │
│   │  (1-2 days) │                                                                │
│   └──────┬──────┘                                                                │
│          │                                                                       │
│          ▼                                                                       │
│   ┌─────────────┐                                                                │
│   │  Phase 1    │  Tool-calling in LLM (Block A)                                 │
│   │  (3-5 days) │  • Hardcoded tools                                            │
│   └──────┬──────┘  • get_reply() with tool-calling                              │
│          │                                                                       │
│          ▼                                                                       │
│   ┌─────────────┐                                                                │
│   │  Phase 2    │  Registry + Loader + Builtin (Blocks B, D)                     │
│   │  (3-5 days) │  • Load from YAML                                             │
│   └──────┬──────┘  • calculator, datetime                                       │
│          │                                                                       │
│          ▼                                                                       │
│   ┌─────────────┐                                                                │
│   │  Phase 3    │  Settings in DB + API (Block C)                               │
│   │  (3-5 days) │  • ToolSettingsModel                                          │
│   └──────┬──────┘  • /api/tools/* endpoints                                     │
│          │                                                                       │
│          ├─────────────────────────────────┐                                    │
│          │                                 │                                    │
│          ▼                                 ▼                                    │
│   ┌─────────────┐                   ┌─────────────┐                             │
│   │  Phase 4    │                   │  Phase 5    │  ← can run in parallel!      │
│   │  (1 week)   │                   │  (3-5 days) │                             │
│   │             │                   │             │                             │
│   │ Admin       │                   │ Admin       │                             │
│   │ Tools       │                   │ Admins      │                             │
│   │ (Block E)   │                   │ (Block F)   │                             │
│   └──────┬──────┘                   └─────────────┘                             │
│          │                                                                       │
│          ▼                                                                       │
│   ┌─────────────┐                                                                │
│   │  Phase 6    │  First business plugin: Worklog Checker                        │
│   │ (1-2 weeks) │  • Jira/Tempo integration                                      │
│   └──────┬──────┘  • E2E test                                                   │
│          │                                                                       │
│          ▼                                                                       │
│   ┌─────────────┐                                                                │
│   │  Phase 7+   │  New plugins as needed                                        │
│   │             │  • HR Service                                                 │
│   │             │  • Reminder (with LLM)                                        │
│   │             │  • ...                                                        │
│   └─────────────┘                                                                │
│                                                                                  │
│                                                                                  │
│   NOTE: Phase 5 (Admin Administrators) can run in parallel with Phases 4 and 6,  │
│   since the API already exists.                                                  │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Plugin structure (standard)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                    PLUGIN ANATOMY                                                │
│                                                                                  │
│   plugins/                                                                       │
│   └── {plugin_name}/                                                             │
│       │                                                                          │
│       ├── plugin.yaml              # Manifest (required)                         │
│       │   │                                                                      │
│       │   ├── id: string           # Unique identifier                           │
│       │   ├── name: string         # Name for UI                                 │
│       │   ├── version: string      # Plugin version                             │
│       │   ├── description: string  # Description for UI                          │
│       │   ├── enabled: bool        # Enabled by default                           │
│       │   │                                                                      │
│       │   ├── tools:               # List of plugin functions (YAML key kept) │
│       │   │   └── - name: string                                                │
│       │   │       description: string (ENGLISH!)                                │
│       │   │       handler: string  # Function name in handlers.py               │
│       │   │       parameters:      # JSON Schema                                │
│       │   │       uses_llm: bool   # Uses LLM (optional)                        │
│       │   │       timeout: int     # Timeout in seconds                         │
│       │   │                                                                      │
│       │   └── settings:            # Plugin settings (optional)                  │
│       │       └── - key: string                                                 │
│       │           label: string                                                 │
│       │           type: string|password|number|select|bool                      │
│       │           required: bool                                                │
│       │           default: any                                                  │
│       │           options: []      # For select                                 │
│       │                                                                          │
│       ├── handlers.py              # Plugin functions (required)                 │
│       │   │                                                                      │
│       │   ├── async def function_name(param1, param2) -> str | dict              │
│       │   │   """Docstring — description for logs"""                            │
│       │   │   ...                                                               │
│       │   │   return result                                                     │
│       │   │                                                                      │
│       │   └── # Can use:                                                         │
│       │       # from tools.base import get_setting, get_llm_client               │
│       │                                                                          │
│       └── (additional files)      # As needed                                   │
│           ├── client.py            # Clients for external APIs                   │
│           ├── models.py            # Pydantic models                             │
│           └── templates.py         # Prompts for LLM                             │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Example plugin.yaml (Worklog Checker)

```yaml
# plugins/worklog_checker/plugin.yaml

id: worklog-checker
name: "Worklog checker"
version: "1.0.0"
description: "Checks employee time logging in Jira/Tempo"
enabled: false  # Requires configuration before enabling

tools:
  - name: check_worklogs
    description: "Checks employee worklogs in Jira/Tempo for a specified period. Returns logged hours, required hours, and deficit."
    handler: check_worklogs
    timeout: 60
    parameters:
      type: object
      properties:
        employee:
          type: string
          description: "Employee name, email, or Jira username"
        period:
          type: string
          description: "Period to check: this_week, last_week, this_month, last_month, or date range (YYYY-MM-DD/YYYY-MM-DD)"
          default: "this_week"
      required:
        - employee

  - name: get_worklog_summary
    description: "Gets worklog summary for a team or department"
    handler: get_worklog_summary
    timeout: 120
    parameters:
      type: object
      properties:
        team:
          type: string
          description: "Team or department name"
        period:
          type: string
          default: "this_week"
      required:
        - team

settings:
  - key: jira_url
    label: "Jira URL"
    type: string
    required: true
    description: "https://your-company.atlassian.net"
  
  - key: jira_email
    label: "Jira Email"
    type: string
    required: true
  
  - key: jira_token
    label: "Jira API Token"
    type: password
    required: true
  
  - key: tempo_token
    label: "Tempo API Token"
    type: password
    required: true
  
  - key: required_hours_per_day
    label: "Required hours per day"
    type: number
    default: 8
  
  - key: working_days
    label: "Working days"
    type: string
    default: "mon,tue,wed,thu,fri"
```

---

## 6. Request processing flow (target)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│  USER: "Check Ivanov's worklogs for this week"                                   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  1. TELEGRAM BOT                                                                 │
│                                                                                  │
│     • Receives message via long polling                                          │
│     • Extracts chat_id, user_id, text                                             │
│     • Passes to Conversation Manager                                             │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  2. CONVERSATION MANAGER                                                         │
│                                                                                  │
│     • Retrieves conversation history for chat_id                                 │
│     • Builds messages: [system, ...history, user_message]                         │
│     • System prompt: ENGLISH                                                     │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  3. LLM ROUTER                                                                   │
│                                                                                  │
│     • Gets plugins (as tools for LLM) from Registry (enabled only)                │
│     • Descriptions of plugin functions: ENGLISH                                  │
│     • Sends request to LLM Provider                                              │
│                                                                                  │
│     Request:                                                                     │
│     {                                                                            │
│       "model": "gpt-4o-mini",                                                    │
│       "messages": [...],                                                         │
│       "tools": [                                                                 │
│         {                                                                        │
│           "type": "function",                                                    │
│           "function": {                                                          │
│             "name": "check_worklogs",                                            │
│             "description": "Checks employee worklogs...",                        │
│             "parameters": {...}                                                  │
│           }                                                                      │
│         }                                                                        │
│       ]                                                                          │
│     }                                                                            │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  4. LLM PROVIDER (OpenAI / Anthropic / etc.)                                     │
│                                                                                  │
│     Response:                                                                    │
│     {                                                                            │
│       "tool_calls": [                                                            │
│         {                                                                        │
│           "id": "call_123",                                                      │
│           "function": {                                                          │
│             "name": "check_worklogs",                                            │
│             "arguments": "{\"employee\": \"Ivanov\", \"period\": \"this_week\"}"      │
│           }                                                                      │
│         }                                                                        │
│       ]                                                                          │
│     }                                                                            │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  5. TOOL EXECUTOR                                                                │
│                                                                                  │
│     • Finds handler in Registry                                                  │
│     • Calls: check_worklogs(employee="Ivanov", period="this_week")                │
│     • Logs the call                                                               │
│     • Handles timeout/errors                                                      │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  6. PLUGIN: worklog_checker                                                      │
│                                                                                  │
│     async def check_worklogs(employee, period):                                  │
│         settings = get_settings("worklog-checker")                               │
│         jira = JiraClient(settings.jira_url, settings.jira_token)                │
│         tempo = TempoClient(settings.tempo_token)                                │
│                                                                                  │
│         worklogs = await tempo.get_worklogs(employee, period)                    │
│         return {                                                                 │
│             "employee": "Ivanov Petr",                                            │
│             "period": "2024-01-08 — 2024-01-12",                                  │
│             "logged_hours": 32,                                                  │
│             "required_hours": 40,                                                │
│             "deficit": 8,                                                        │
│             "tasks_without_logs": ["PROJ-123", "PROJ-456"]                       │
│         }                                                                        │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  7. LLM ROUTER (continued)                                                       │
│                                                                                  │
│     • Appends tool_result to messages                                            │
│     • Sends follow-up request to LLM                                             │
│     • LLM formulates reply in user language                                       │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  8. TELEGRAM BOT                                                                 │
│                                                                                  │
│     • Sends reply to user                                                         │
│     • Saves to history                                                           │
│                                                                                  │
│     "Ivanov Petr this week (08.01 — 12.01):                                      │
│      • Logged: 32 hours                                                          │
│      • Required: 40 hours                                                        │
│      • Deficit: 8 hours                                                          │
│                                                                                  │
│      Tasks without logs: PROJ-123, PROJ-456"                                     │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Resources and constraints

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                    RESOURCES (Mac Mini)                                           │
│                                                                                  │
│   What we use:                                                                   │
│   ├── 1 Python process (uvicorn + bot subprocess)                               │
│   ├── SQLite (file ~1-10 MB)                                                    │
│   ├── RAM: ~100-300 MB                                                          │
│   └── CPU: minimal load (long polling, periodic requests)                      │
│                                                                                  │
│   What we do NOT use:                                                            │
│   ├── ❌ PostgreSQL                                                              │
│   ├── ❌ Redis                                                                   │
│   ├── ❌ Message Broker                                                          │
│   ├── ❌ Separate containers per service                                        │
│   └── ❌ Kubernetes                                                              │
│                                                                                  │
│   Token optimization:                                                            │
│   ├── System prompt: English                                                     │
│   ├── Plugin (function) descriptions: English                                    │
│   ├── Short descriptions                                                        │
│   ├── Model: GPT-4o-mini or Gemini Flash                                        │
│   └── Savings: ~20-25%                                                          │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Scaling path (future)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│   Mac Mini (now)                         Corporate environment (later)           │
│   ─────────────────                     ─────────────────────────               │
│                                                                                  │
│   Single process       ───────────►      Can keep the same                       │
│                                         OR                                       │
│                                         Heavy plugins → separate services        │
│                                                                                  │
│   SQLite               ───────────►     PostgreSQL (if needed)                  │
│                                                                                  │
│   Plugins as modules   ───────────►      type: external in plugin.yaml           │
│                                         (HTTP endpoint instead of local)         │
│                                                                                  │
│   ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│   Example plugin migration:                                                      │
│                                                                                  │
│   # Before (local)                     # After (external)                      │
│   type: local                           type: external                          │
│   handler: check_worklogs               endpoint: http://worklog-svc:8001         │
│                                         path: /api/check                         │
│                                                                                  │
│   Core code does not change!                                                    │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Summary

| Component | Status | Phase |
|-----------|--------|-------|
| Telegram Bot | No changes | — |
| LLM Provider Adapter | Extension (tool-calling) | 1 |
| Admin API (TG, LLM, Admins) | No changes | — |
| Admin panel (Settings) | No changes | — |
| **Tool-calling in LLM** | **NEW** | 1 |
| **Tool Registry** | **NEW** | 2 |
| **Plugin Loader** | **NEW** | 2 |
| **Builtin plugins** | **NEW** | 2 |
| **Tool settings in DB** | **NEW** | 3 |
| **Tools API** | **NEW** | 3 |
| **Admin panel (Tools)** | **NEW** | 4 |
| **Admin panel (Administrators)** | **NEW** | 5 |
| **Worklog Checker plugin** | **NEW** | 6 |

**Total time:** 6–8 weeks to a fully working system with the first business plugin.

---

## Versioning

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-02-06 | First version of target architecture |
| 1.1 | 2026-02-06 | (in progress) |
| 1.2 | 2026-02-07 | Terminology: plugin = tool for orchestrator; plugin has functions (not tools). Section Terminology, Plugin anatomy and blocks updated. |
