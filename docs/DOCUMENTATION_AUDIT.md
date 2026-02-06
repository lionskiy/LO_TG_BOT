# Documentation Audit Report

> **Purpose:** Identify weak architectural decisions, insufficient task descriptions, and documentation issues that may hinder quality implementation.  
> **Date:** 2026-02-07  
> **Scope:** ARCHITECTURE_BLUEPRINT.md, UPGRADE_TASKS.md, PLAN_PHASE_0_1 through PLAN_PHASE_6.md

---

## 1. Executive Summary

- **Strengths:** Phase 0–1 and Phase 2 are well specified with clear “Done when” criteria, signatures, and provider notes. Architecture is consistent and phased.
- **Risks:** (1) Tool settings stored per-tool while plugins define settings at plugin level (possible duplication/ambiguity). (2) Phase 6 “team” resolution and Jira/Tempo endpoint details are left TBD. (3) No single contract for tool error response format or plugin test handler. (4) Language/encoding mix: PLAN_PHASE_4/5/6 contain Russian and corrupted text (e.g. `toolмand`, `прand`, `еслand`), which hurts readability and tooling.
- **Recommendations:** Clarify settings storage (per-tool vs per-plugin), add a short “Contracts” section (tool errors, test handler), fix encoding/typos, and add Phase 6 endpoint/team references.

---

## 2. Architectural Weaknesses

### 2.1 Tool settings: per-tool vs per-plugin

- **Where:** ARCHITECTURE_BLUEPRINT (Storage), PLAN_PHASE_3 (ToolSettingsModel), UPGRADE_TASKS (Tools Repository).
- **Issue:** The DB table `tool_settings` uses `tool_name` as primary key, so each **tool** has its own row and its own `settings_json`. Many plugins (e.g. Worklog Checker) define **plugin-level** settings (Jira URL, tokens) shared by all tools in that plugin. The docs do not state whether:
  - (A) Settings are duplicated per tool (e.g. two rows for `check_worklogs` and `get_worklog_summary` with the same Jira/Tempo config), or
  - (B) Settings are stored once per plugin and referenced by tools (would require a different schema or a `plugin_settings` table).
- **Impact:** Implementers may duplicate settings per tool or introduce a plugin-level store without a documented standard; admin UI and “needs_config” logic may diverge.
- **Recommendation:** Decide and document: either “one row per tool, settings duplicated when shared” with a clear convention, or introduce a `plugin_settings` (or similar) table and document that tools of the same plugin read from it. Mention in ARCHITECTURE_BLUEPRINT and Phase 3.

### 2.2 Registry “enabled” state in Phase 2 vs Phase 3

- **Where:** PLAN_PHASE_2 (Registry), PLAN_PHASE_3 (Storage + API).
- **Issue:** Phase 2 says plugin settings are not in DB yet; Registry has `enable_tool` / `disable_tool` and in-memory state. Phase 3 adds DB. The **startup sequence** (load plugins → load tool_settings from DB → apply enabled flags to Registry) is not explicitly described in one place. UPGRADE_TASKS 4.3.2 says “Sync Registry with DB” but does not spell out the order (plugins load first, then DB overlay).
- **Impact:** Risk of Registry and DB getting out of sync, or of tools appearing enabled in UI but not in runtime (or vice versa).
- **Recommendation:** Add a short “Startup and sync” subsection in ARCHITECTURE_BLUEPRINT or Phase 3: (1) Load plugins and register tools, (2) Load tool_settings from DB, (3) For each tool_name, set Registry enabled state from DB (and “needs_config” from schema vs settings).

### 2.3 LLM response: content and tool_calls together

- **Where:** PLAN_PHASE_0_1 (Task 1.1, get_reply behaviour).
- **Issue:** The spec says: if LLM returns text → `(content, None)`; if tool_calls → `(None, [ToolCall])`. Some providers can return **both** content and tool_calls in one response. The intended behaviour (e.g. prefer tool_calls, or merge) is not defined.
- **Impact:** Divergent behaviour across providers or inconsistent handling of combined responses.
- **Recommendation:** In Phase 0–1, add one sentence: “If the API returns both content and tool_calls, prefer tool_calls for the loop; optionally append content to messages as assistant message.”

### 2.4 ARCHITECTURE_BLUEPRINT Summary table vs Phase 1

- **Where:** ARCHITECTURE_BLUEPRINT.md, section 9 Summary.
- **Issue:** Table row “LLM Provider Adapter” is marked “No changes”; Phase 1 extends it for tool-calling.
- **Recommendation:** Change to “Extension (tool-calling)” and phase “1”.

---

## 3. Insufficient or Ambiguous Task Descriptions

### 3.1 Phase 1 — Provider coverage and return-type edge case

- **Task 1.1** lists OpenAI, Anthropic, Google with examples; Groq, OpenRouter, Ollama are “basic tool-calling”. It does not list **which files/functions** to change per provider (e.g. `bot/llm.py` and provider-specific blocks). New contributors may miss a provider.
- **Recommendation:** Add a small table: Provider → File(s) / function(s) to modify; and “Groq/OpenRouter/Ollama: reuse OpenAI-compatible path if applicable, else document as best-effort”.

### 3.2 Phase 2 — Where and when plugins are loaded

- **Task 2.3** describes `load_all_plugins()` but not **where** it is invoked (e.g. `api/app.py` lifespan or `main.py`). Phase 3 diagram shows “startup” but the exact call site is not in Phase 2.
- **Recommendation:** In Phase 2, add “Integration: call `load_all_plugins()` from api/app.py startup (or main.py) so Registry is populated before handling requests.”

### 3.3 Phase 3 — Duplicate section headers

- **Where:** PLAN_PHASE_3.md.
- **Issue:** Multiple “## Phase 3” headers (e.g. around lines 47, 56, 123) make navigation and “current section” ambiguous.
- **Recommendation:** Use distinct headings (e.g. “Phase 3 goal”, “Phase 3 architecture”, “Task 3.1 …”).

### 3.4 Phase 4 — Mixed language and encoding

- **Where:** PLAN_PHASE_4.md.
- **Issue:** Section titles and body mix Russian and English; there are encoding glitches (e.g. “toolмand”, “Кнопкand”, “настроек”, “еслand”). “Before (after Phase 3)” line has “toolмand” instead of “tools”.
- **Impact:** Harder for English-only implementers and for automated indexing/search.
- **Recommendation:** Fix obvious encoding/typo errors; consider an English-only version of Phase 4 (and 5/6) or a short English “Task summary” at the top.

### 3.5 Phase 6 — Team resolution and API endpoints

- **get_worklog_summary(team, period):** The doc says team → list of users “через Jira API группы/проекта or заранее заданный list в настройках — уточнить в спеках”. So **how** to resolve “team” to users is explicitly TBD.
- **Impact:** Implementers may invent different solutions (e.g. Jira group ID, custom setting, or “team” ignored in v1).
- **Recommendation:** Either (a) Define “team” for v1: e.g. “optional; if provided, treat as comma-separated Jira usernames from settings” or “Jira group name + API call X”, or (b) State “team support deferred; get_worklog_summary(period) only” and add a follow-up task.

- **Jira/Tempo endpoints:** The doc asks to “указать в спеках or в отдельной таблице «Эндпоинты»” but no such table exists. Implementation is left to “look up in official docs”.
- **Recommendation:** Add a “Reference endpoints” subsection with at least: Tempo worklogs URL pattern (e.g. base + `/worklogs`), Jira user search and (if used) issue search; and note “exact paths depend on Tempo/Jira version (e.g. v2/v3).”

### 3.6 Shared contracts not centralized

- **Tool error response:** Phase 1 and Phase 6 say “return error message in tool result” but not the **format** (plain text “Error: …” vs JSON `{ "error": "…" }`). LLM and tests need a stable contract.
- **Plugin test handler:** Phase 6 describes a test handler returning `{ "jira_ok", "tempo_ok", "errors" }`; Phase 3/4 mention `POST /api/tools/{name}/test`. The way the API wraps the handler response (status code, body shape) is not in one place.
- **Recommendation:** Add a short “Contracts” section (in ARCHITECTURE_BLUEPRINT or a new CONTRACTS.md): (1) Tool error result format (e.g. string starting with “Error:” or a small JSON schema), (2) Plugin test handler: expected return shape and how the API maps it to HTTP response.

---

## 4. Language and Encoding Issues

- **PLAN_PHASE_4.md:** Mixed Russian/English; corrupted/encoding words: “toolмand”, “Кнопкand”, “настроек”, “еслand”, “плагиon”, “настроек”, “интеграциand”, “полями”, “соответствующимand”, “Трand”, “карточках”, “валидациand”, “пункты”, “пройдены”.
- **PLAN_PHASE_5.md:** Same pattern: “администраторамand”, “навигациand”, “прand”, “эндпоинты”, “еслand”, “макетоin”, “админкand”, “Контейнер”, “стor”, “таблицand”, “кнопкand”, “открытиand”, “загружать”, “пройдены”, etc.
- **PLAN_PHASE_6.md:** “Наvalue”, “ворклогand”, “часоin”, “Documentация”, “Версиand”, “настроек”, “идентификатороin”, “админкand”, “сценариand”, “пройдены”, “админкand”, etc.

**Recommendation:**  
- Fix clear encoding/typo bugs (e.g. “toolмand” → “tools”, “Наvalue” → “Value” in context) so the intended word is unambiguous.  
- Keep or translate Russian intentionally: either add an English version of Phase 4/5/6 task summaries or leave Russian as-is and note in this audit that non-Russian readers may need a separate translation.

---

## 5. Minor Inconsistencies

| Item | Location | Suggestion |
|------|----------|------------|
| ToolCall/ToolResult ownership | Phase 1 (llm.py or models.py), Phase 2 (tools/models.py) | Phase 1 could say: “In Phase 2 these will move to tools/models.py.” |
| Plugin manifest “enabled” | plugin.yaml has `enabled: true/false`; DB has per-tool `enabled` | Clarify: manifest = default; DB overrides after first save. |
| Phase 5 prerequisite | “For единой навигации желательно завершение Фазы 4” | Already states Phase 5 can run in parallel; keep, fix encoding if desired. |

---

## 6. Checklist for Implementers

Before implementation, ensure:

- [ ] Tool settings strategy (per-tool vs per-plugin) is decided and documented.
- [ ] Startup order (plugins → DB → Registry sync) is written in Phase 3 or ARCHITECTURE.
- [ ] Phase 1: Behaviour when LLM returns both content and tool_calls is defined.
- [ ] Phase 2: Call site for `load_all_plugins()` is specified.
- [ ] Phase 6: “team” resolution for get_worklog_summary is defined or explicitly deferred; reference endpoints for Jira/Tempo are listed.
- [ ] A single “Contracts” section or file describes tool error format and plugin test handler response.
- [ ] Encoding/typos in PLAN_PHASE_4/5/6 are fixed where they change meaning (e.g. “toolмand” → “tools”).

---

## 7. Applied fixes (2026-02-07)

The following were applied after the audit:

- **ARCHITECTURE_BLUEPRINT.md:** Summary table — "LLM Provider Adapter" set to "Extension (tool-calling)" and Phase 1.
- **PLAN_PHASE_3.md:** Duplicate "## Phase 3" headers replaced with "Phase 3 goal and scope" and "Phase 3 architecture diagram".
- **PLAN_PHASE_4.md:** Typo "toolмand" corrected to "tools" in the "Before (after Phase 3)" line.
- **PLAN_PHASE_0_1.md:** Clarified behaviour when provider returns both content and tool_calls; added note that ToolCall moves to tools/models.py in Phase 2.

Remaining recommendations (tool settings strategy, startup/sync description, Phase 6 team and endpoints, shared Contracts section, and full encoding cleanup in Phase 4/5/6) are left for follow-up.

---

## 8. Document Versioning

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-02-07 | Initial audit report |
