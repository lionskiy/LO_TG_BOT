# PHASE 0-1: Stabilization and Tool-Calling

> **Detailed task specification for Phases 0 and 1**  
> Prepare the base and add tool-calling to the LLM Engine

**Version:** 1.1  
**Date:** 2026-02-06  
**Estimated duration:** 5–7 days

---

## Related documents

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target system architecture | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Full task breakdown | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Detailed plan for Phase 0–1 (this document) | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Detailed plan for Phase 2 (next phase) | ✅ Current (in progress) |

### Current implementation (v1.0)

| Document | Description |
|----------|-------------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Current implementation specification |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

---

## Phase navigation

| Phase | Document | Description | Status |
|-------|----------|-------------|--------|
| 0-1 | **[PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md)** | Stabilization + Tool-Calling | ✅ Current (in progress) |
| 2 | [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Plugin System | ✅ Current (in progress) |
| 3 | [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Storage + API | ✅ Current (in progress) |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Admin Tools | ✅ Current (in progress) |
| 5 | [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Admin Administrators | ✅ Current (in progress) |
| 6 | [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Worklog Checker | ✅ Current (in progress) |

---

## Overall goal of Phases 0–1

**Before:** Bot receives message → sends to LLM → returns text reply.

**After:** Bot receives message → sends to LLM with tool descriptions → LLM may call a tool → tool result is sent back to LLM → final reply to user.

**Important:** Current behaviour must remain unchanged. Tool-calling is an addition, not a replacement.

---

# PHASE 0: Stabilization

**Goal:** Freeze working state, ensure tests exist, prepare branch for work.

**Duration:** 1–2 days

---

## Task 0.1: Review current state

### Description
Verify that the current implementation works correctly, all tests pass, and documentation is up to date.

### Steps
1. Run all existing tests: `pytest tests/`
2. Verify the bot starts in both modes:
   - `python main.py` (settings from .env)
   - `uvicorn api.app:app` (settings from DB)
3. Verify admin panel:
   - Telegram settings (save, test, activate)
   - LLM settings (save, test, activate)
   - Hot-swap works
4. Verify the bot replies to messages via the configured LLM

### Done when
- [ ] All tests pass (`pytest tests/` — green)
- [ ] Bot works in main.py mode
- [ ] Bot works in uvicorn + subprocess mode
- [ ] Admin panel works
- [ ] Documentation matches reality

---

## Task 0.2: Test additions (if needed)

### Description
Add missing tests for critical paths that will be touched in Phase 1.

### What should be covered
1. **bot/llm.py — get_reply()**
   - Test: successful LLM response
   - Test: LLM error handling (timeout, API error)
   - Test: settings from DB (priority over .env)

2. **bot/telegram_bot.py — message handling**
   - Test: conversation history is kept
   - Test: history limit (20 pairs)

3. **api/app.py — startup/shutdown**
   - Test: application starts without errors
   - Test: bot subprocess starts when active settings exist

### Done when
- [ ] Critical paths in bot/llm.py covered
- [ ] Tests do not depend on real APIs (mocking)

---

## Task 0.3: Create branch and tag

### Description
Freeze current state for possible rollback.

### Steps
1. Create tag for current state: `git tag v0.9-pre-tools`
2. Create branch for work: `git checkout -b feature/tool-calling`
3. Ensure CI (if any) passes on current state

### Done when
- [ ] Tag created and pushed
- [ ] Branch created
- [ ] Can roll back to stable state

---

## Task 0.4: Prepare structure for new modules

### Description
Create empty files and folders for new modules so imports work.

### Structure
```
LO_TG_BOT/
├── bot/
│   ├── llm.py                  # existing
│   └── tool_calling.py         # NEW (empty for now)
│
├── tools/                      # NEW FOLDER
│   └── __init__.py             # empty
│
└── plugins/                    # NEW FOLDER
    └── __init__.py             # empty
```

### Done when
- [ ] Folder tools/ created with __init__.py
- [ ] Folder plugins/ created with __init__.py
- [ ] File bot/tool_calling.py created (can be empty or with TODO)
- [ ] Imports do not break existing code

---

# PHASE 1: Tool-Calling in LLM Engine

**Goal:** LLM can call tools. For now tools are hardcoded (2 test ones).

**Duration:** 3–5 days

**Principle:** Minimal changes to existing code. New logic in new files.

---

## Phase 1 architecture overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  telegram_bot.py                                                            │
│  │                                                                          │
│  │  handle_message()                                                        │
│  │  ├── Builds messages (system + history + user)                          │
│  │  ├── Calls get_reply(messages)             ← CHANGE                     │
│  │  └── Sends reply to user                                                 │
│  │                                                                          │
│  └──────────────────────────┬──────────────────────────────────────────────┘
│                             │
│                             ▼
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                                                                         │
│  │  llm.py — get_reply(messages, tools=None)         ← EXTENSION          │
│  │  │                                                                      │
│  │  │  If tools=None:                                                      │
│  │  │  └── Works as before (no changes)                                    │
│  │  │                                                                      │
│  │  │  If tools provided:                                                  │
│  │  │  └── Passes tools to LLM API                                         │
│  │  │  └── Returns (content, tool_calls)                                   │
│  │  │                                                                      │
│  │  └──────────────────────────────────────────────────────────────────────┘
│                             │
│                             ▼
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                                                                         │
│  │  tool_calling.py — get_reply_with_tools(messages)       ← NEW          │
│  │  │                                                                      │
│  │  │  1. Gets tools from HARDCODED_TOOLS                                   │
│  │  │  2. Calls llm.get_reply(messages, tools)                            │
│  │  │  3. If tool_calls present:                                           │
│  │  │     ├── Executes tools                                               │
│  │  │     ├── Appends results to messages                                  │
│  │  │     └── Repeats request to LLM                                       │
│  │  │  4. Returns final text reply                                         │
│  │  │                                                                      │
│  │  └──────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Conversation history with tool-calling:** only the **final text reply** to the user is stored in history. Intermediate messages (assistant with tool_calls, tool results) are not written to history.

---

## Task 1.1: Extend get_reply() to support tools

### Description
Modify `get_reply()` in `bot/llm.py` so it can accept an optional `tools` parameter and return tool_calls information.

### Current signature
```python
async def get_reply(messages: List[dict]) -> str
```

### New signature
```python
async def get_reply(
    messages: List[dict], 
    tools: List[dict] | None = None,
    tool_choice: str | None = "auto"
) -> tuple[str, List[ToolCall] | None]
```

### Behaviour

**Without tools (backward compatible):**
- If `tools=None`, function works as before
- Returns `(content, None)`

**With tools:**
- Passes `tools` and `tool_choice` to LLM API
- If LLM returned tool_calls, returns `(None, [ToolCall(...)])`
- If LLM returned text, returns `(content, None)`

### ToolCall structure
```python
@dataclass
class ToolCall:
    id: str              # Unique call ID (from LLM)
    name: str            # Tool name
    arguments: dict      # Arguments (already parsed JSON)
```

### Provider-specific changes

#### OpenAI / OpenAI-compatible (Groq, OpenRouter, Ollama, etc.)
```
Request:
  tools: [...]
  tool_choice: "auto"

Response:
  message.tool_calls: [
    {
      id: "call_abc123",
      function: {
        name: "get_current_datetime",
        arguments: "{}"
      }
    }
  ]
```

#### Anthropic (Claude)
```
Request:
  tools: [...]  # Anthropic format differs

Response:
  content: [
    {
      type: "tool_use",
      id: "toolu_01...",
      name: "get_current_datetime",
      input: {}
    }
  ]
```

#### Google (Gemini)
```
Request:
  tools: [...]  # Gemini format

Response:
  candidates[0].content.parts: [
    {
      function_call: {
        name: "get_current_datetime",
        args: {}
      }
    }
  ]
```

### Tasks
1. Add dataclass `ToolCall` in bot/llm.py (or separate models.py)
2. Modify each provider to support tools
3. Unify parsing of tool_calls into ToolCall
4. Add tool converters between formats (if needed)

### Done when
- [ ] get_reply() accepts optional tools parameter
- [ ] Without tools — works as before (no regression)
- [ ] With tools — returns ToolCall for OpenAI
- [ ] With tools — returns ToolCall for Anthropic
- [ ] With tools — returns ToolCall for Google
- [ ] Tests for all cases

---

## Task 1.2: Create tool_calling.py module

### Description
New module that orchestrates tool-calling: gets tools, calls LLM, executes tools, returns final reply.

### File: bot/tool_calling.py

### Main function
```python
async def get_reply_with_tools(
    messages: List[dict],
    max_iterations: int = 5
) -> str
```

### Algorithm

```
1. PREPARE
   │
   ├── Get tools list (HARDCODED_TOOLS for now)
   ├── If tools empty → call plain get_reply() without tools
   │
2. TOOL-CALLING LOOP (max_iterations)
   │
   ├── Call get_reply(messages, tools)
   │   │
   │   ├── If text (content) returned → EXIT, return content
   │   │
   │   └── If tool_calls returned:
   │       │
   │       ├── For each tool_call:
   │       │   ├── Find handler by name
   │       │   ├── Execute handler(arguments)
   │       │   └── Store result
   │       │
   │       ├── Append to messages:
   │       │   ├── assistant message with tool_calls
   │       │   └── tool result messages
   │       │
   │       └── Continue loop
   │
3. LOOP GUARD
   │
   └── If max_iterations reached → return fallback reply
```

### Tool result message format (OpenAI)
```python
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "2024-01-15 14:30:00"
}
```

### Tool result message format (Anthropic)
```python
{
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_01...",
            "content": "2024-01-15 14:30:00"
        }
    ]
}
```

### Error handling

| Situation | Behaviour |
|-----------|-----------|
| Tool not found | Return error message in tool result |
| Tool raised exception | Return error message in tool result |
| Execution timeout | Return timeout error in tool result |
| max_iterations reached | Return text: "Could not complete the operation" |
| LLM API error | Re-raise exception (as before) |

### Done when
- [ ] get_reply_with_tools() implemented
- [ ] Tool-calling loop works
- [ ] Tool results correctly appended to messages
- [ ] Infinite loop guard in place
- [ ] Tool execution error handling
- [ ] Tests for tool-calling loop

---

## Task 1.3: Hardcoded test tools

### Description
Create 2 simple tools in code for testing tool-calling. In Phase 2 they will be moved to plugins.

### Tool 1: get_current_datetime

**Description (for LLM, English):**
```
Returns current date and time in ISO format with weekday name.
```

**Parameters:** None

**Behaviour:**
- Returns current date and time
- Format: "2024-01-15 14:30:00 (Monday)"
- Uses UTC or local time (configurable)

**Tool definition (OpenAI format):**
```json
{
  "type": "function",
  "function": {
    "name": "get_current_datetime",
    "description": "Returns current date and time in ISO format with weekday name",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  }
}
```

**Handler:**
```python
async def get_current_datetime() -> str:
    # Returns current time
```

### Tool 2: calculate

**Description (for LLM, English):**
```
Evaluates a mathematical expression and returns the result. 
Supports: +, -, *, /, **, parentheses, sqrt, sin, cos, tan, log, pi, e.
```

**Parameters:**
- `expression` (string, required) — mathematical expression

**Tool definition:**
```json
{
  "type": "function",
  "function": {
    "name": "calculate",
    "description": "Evaluates a mathematical expression and returns the result. Supports: +, -, *, /, **, parentheses, sqrt, sin, cos, tan, log, pi, e.",
    "parameters": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "Mathematical expression to evaluate, e.g. '2 + 2 * 3' or 'sqrt(16)'"
        }
      },
      "required": ["expression"]
    }
  }
}
```

**Handler:**
```python
async def calculate(expression: str) -> str:
    # Safe eval with limited function set
    # Returns result or error message
```

**Security:**
- Use a limited set of allowed functions
- Do not use `eval()` directly
- Use `ast.literal_eval` or the `simpleeval` library

### Structure in code
```python
# bot/tool_calling.py

HARDCODED_TOOLS = [
    {
        "definition": { ... },  # OpenAI format
        "handler": get_current_datetime
    },
    {
        "definition": { ... },
        "handler": calculate
    }
]
```

### Done when
- [ ] get_current_datetime works
- [ ] calculate works with basic operations
- [ ] calculate is safe (no code injection)
- [ ] Tool definitions correct for OpenAI
- [ ] Tests for both tools

---

## Task 1.4: Integration in telegram_bot.py

### Description
Wire tool-calling into the message handler. There must be a way to enable/disable tool-calling.

### Current flow (simplified)
```python
# telegram_bot.py

async def handle_message(update, context):
    messages = build_messages(chat_id, text)
    reply = await get_reply(messages)
    await update.message.reply_text(reply)
    save_to_history(chat_id, text, reply)
```

### New flow
```python
# telegram_bot.py

async def handle_message(update, context):
    messages = build_messages(chat_id, text)
    
    if tools_enabled():  # Flag check
        reply = await get_reply_with_tools(messages)
    else:
        reply = await get_reply(messages)
    
    await update.message.reply_text(reply)
    save_to_history(chat_id, text, reply)
```

### Tool-calling enable flag

**Options (choose one):**

1. **Environment variable:**
   ```
   ENABLE_TOOL_CALLING=true
   ```

2. **DB setting (in LLM settings):**
   ```python
   llm_settings.enable_tools = True
   ```

3. **Always on** (for Phase 1, simplification):
   ```python
   # For now just always use tools
   reply = await get_reply_with_tools(messages)
   ```

**Recommendation for Phase 1:** Use environment variable `ENABLE_TOOL_CALLING=true`. This allows quick rollback if something goes wrong.

### Error handling

Tool-calling must not break the bot. If something goes wrong:
```python
try:
    reply = await get_reply_with_tools(messages)
except Exception as e:
    logger.error(f"Tool-calling failed: {e}, falling back to regular reply")
    reply = await get_reply(messages)  # Fallback
```

### Done when
- [ ] Tool-calling integrated in telegram_bot.py
- [ ] Flag to enable/disable exists
- [ ] Fallback to normal mode on errors
- [ ] Tool-calls logging
- [ ] Conversation history saved correctly

---

## Task 1.5: System prompt for tool-calling

### Description
Update system prompt so the LLM knows how to use tools and always replies in Russian.

### Current system prompt
```
You are a helpful assistant. Answer the user's questions.
```

### New system prompt (English to save tokens)
```
You are a helpful assistant in a Telegram bot.

IMPORTANT RULES:
1. Always respond in Russian, regardless of this prompt being in English.
2. You have access to tools. Use them when they can help answer the user's question.
3. For date/time questions, use the get_current_datetime tool.
4. For calculations, use the calculate tool.
5. If a tool returns an error, explain it to the user in a friendly way.
6. Do not mention that you're using tools unless the user asks.

Be concise and helpful.
```

### Where it is stored

1. **Default** — in code (bot/config.py or bot/tool_calling.py)
2. **Override** — in LLM settings in DB (existing systemPrompt field)

### Logic
```python
def get_system_prompt():
    # 1. Check DB settings
    db_settings = get_llm_settings()
    if db_settings and db_settings.system_prompt:
        return db_settings.system_prompt
    
    # 2. Use default with tools
    return DEFAULT_SYSTEM_PROMPT_WITH_TOOLS
```

### Done when
- [ ] New system prompt created
- [ ] Prompt in English (saves tokens)
- [ ] Instruction to reply in Russian
- [ ] Prompt used when tool-calling
- [ ] Can override via admin panel

---

## Task 1.6: Phase 1 testing

### Description
Write tests for all new components and perform manual testing.

### Unit tests

#### test_tool_calling.py
```
test_get_current_datetime_returns_valid_format
test_calculate_basic_operations
test_calculate_with_functions (sqrt, sin, etc.)
test_calculate_handles_errors
test_calculate_safe_from_injection

test_get_reply_with_tools_no_tool_call
test_get_reply_with_tools_single_tool_call
test_get_reply_with_tools_multiple_tool_calls
test_get_reply_with_tools_max_iterations
test_get_reply_with_tools_tool_error_handling
```

#### test_llm_tools.py (extend existing)
```
test_get_reply_with_tools_openai
test_get_reply_with_tools_anthropic
test_get_reply_with_tools_google
test_get_reply_without_tools_unchanged
```

### Integration tests

```
test_full_flow_datetime_question
test_full_flow_calculation_question
test_full_flow_regular_question_no_tools
test_fallback_on_tool_error
```

### Manual testing (checklist)

**Setup:**
- [ ] Bot running with `ENABLE_TOOL_CALLING=true`
- [ ] LLM configured (OpenAI or other with tools support)

**Datetime tests:**
- [ ] "What time is it?" → reply with current time
- [ ] "What day of the week is it?" → correct day
- [ ] "What time is it?" (any language) → reply with time

**Calculate tests:**
- [ ] "Calculate 2+2" → "4"
- [ ] "What is 15% of 200?" → "30"
- [ ] "Square root of 144?" → "12"
- [ ] "sin(0) + cos(0)" → "1"

**Tests without tools:**
- [ ] "Hi, how are you?" → normal reply (no tool calls)
- [ ] "Tell me a joke" → normal reply

**Error tests:**
- [ ] "Calculate 1/0" → clear error message
- [ ] "Calculate abc" → clear error message

**Compatibility tests:**
- [ ] Conversation history works
- [ ] Bot does not crash on long conversations
- [ ] Admin panel works as before

### Done when
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] No regressions in existing functionality

---

## Work sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 1: Phase 0                                                             │
│                                                                             │
│  Morning:                                                                    │
│  ├── 0.1 Review current state                                              │
│  └── 0.2 Test additions (if needed)                                         │
│                                                                             │
│  Afternoon:                                                                  │
│  ├── 0.3 Create branch and tag                                              │
│  └── 0.4 Prepare structure for new modules                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 2: Task 1.1 — Extend get_reply()                                      │
│                                                                             │
│  ├── Add ToolCall dataclass                                                 │
│  ├── Modify OpenAI provider                                                 │
│  ├── Modify Anthropic provider                                              │
│  ├── Modify Google provider                                                 │
│  └── Tests                                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 3: Tasks 1.2 + 1.3 — tool_calling.py + tools                           │
│                                                                             │
│  Morning:                                                                    │
│  ├── Create bot/tool_calling.py                                             │
│  ├── Implement get_reply_with_tools()                                       │
│  └── Tool-calling loop                                                      │
│                                                                             │
│  Afternoon:                                                                  │
│  ├── Implement get_current_datetime                                         │
│  ├── Implement calculate                                                    │
│  └── Tool tests                                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 4: Tasks 1.4 + 1.5 — Integration + System prompt                       │
│                                                                             │
│  Morning:                                                                    │
│  ├── Integration in telegram_bot.py                                         │
│  ├── ENABLE_TOOL_CALLING flag                                               │
│  └── Fallback logic                                                         │
│                                                                             │
│  Afternoon:                                                                  │
│  ├── New system prompt                                                      │
│  ├── Tool-calls logging                                                     │
│  └── Integration tests                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DAY 5: Task 1.6 — Testing                                                 │
│                                                                             │
│  ├── Complete unit tests                                                    │
│  ├── Integration tests                                                     │
│  ├── Manual testing per checklist                                           │
│  ├── Bug fixes                                                              │
│  └── Documentation updates                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1 OUTCOME                                                            │
│                                                                             │
│  ✅ Bot can use tools                                                       │
│  ✅ 2 test tools work (datetime, calculator)                                │
│  ✅ Tool-calling works for OpenAI, Anthropic, Google                         │
│  ✅ Can enable/disable via env                                              │
│  ✅ Current functionality intact                                            │
│  ✅ Foundation ready for Phase 2 (Plugin System)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM does not call tools | Medium | High | Improve system prompt, check tools format |
| Different tool-calling formats per provider | High | Medium | ToolCall abstraction, converters |
| Tool-calling slows responses | Medium | Medium | Disable flag, timing logs |
| calculate unsafe | Low | High | Use simpleeval, injection tests |
| Regressions in existing code | Medium | High | Tests, fallback, gradual integration |

---

## Definition of Done for Phase 1

- [ ] All tasks 0.1–0.4 done
- [ ] All tasks 1.1–1.6 done
- [ ] All unit tests pass
- [ ] Manual testing done
- [ ] No regressions (existing tests pass)
- [ ] Code reviewed
- [ ] Branch ready to merge (or to continue in Phase 2)
- [ ] Documentation updated (README, CURRENT_IMPLEMENTATION.md)

---

## Document versioning

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-02-06 | First version of Phase 0–1 plan |
