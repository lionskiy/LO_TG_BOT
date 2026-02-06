"""
Orchestrates tool-calling: gets tools, calls LLM, executes tools, returns final reply.
Phase 1: hardcoded tools (get_current_datetime, calculate). Phase 2 will use plugins.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

from bot.llm import ToolCall, get_reply

logger = logging.getLogger(__name__)

# Default system prompt when using tools (English to save tokens; instructs reply in Russian)
DEFAULT_SYSTEM_PROMPT_WITH_TOOLS = """You are a helpful assistant in a Telegram bot.

IMPORTANT RULES:
1. Always respond in Russian, regardless of this prompt being in English.
2. You have access to tools. Use them when they can help answer the user's question.
3. For date/time questions, use the get_current_datetime tool.
4. For calculations, use the calculate tool.
5. If a tool returns an error, explain it to the user in a friendly way.
6. Do not mention that you're using tools unless the user asks.

Be concise and helpful."""

# ---- Hardcoded tools (Phase 2: move to plugins) ----

async def get_current_datetime() -> str:
    """Returns current date and time in ISO format with weekday name (UTC)."""
    now = datetime.utcnow()
    weekday = now.strftime("%A")
    return now.strftime(f"%Y-%m-%d %H:%M:%S ({weekday})")


async def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression safely. Supports: +, -, *, /, **, sqrt, sin, cos, tan, log, pi, e.
    Uses simpleeval to avoid code injection.
    """
    try:
        from simpleeval import simple_eval, NameNotDefinedError
    except ImportError:
        return "Error: simpleeval is not installed. Cannot evaluate expressions."
    if not expression or not str(expression).strip():
        return "Error: expression is empty."
    expr = str(expression).strip()
    try:
        result = simple_eval(expr)
        if result is None:
            return "Error: expression did not produce a value."
        return str(result)
    except NameNotDefinedError as e:
        return f"Error: unknown symbol or function — {e!s}"
    except Exception as e:
        return f"Error: {e!s}"


# OpenAI-format tool definitions for LLM
TOOL_DEF_GET_CURRENT_DATETIME = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": "Returns current date and time in ISO format with weekday name",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}
TOOL_DEF_CALCULATE = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Evaluates a mathematical expression and returns the result. Supports: +, -, *, /, **, parentheses, sqrt, sin, cos, tan, log, pi, e.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate, e.g. '2 + 2 * 3' or 'sqrt(16)'",
                },
            },
            "required": ["expression"],
        },
    },
}

HARDCODED_TOOL_HANDLERS: Dict[str, Callable[..., Any]] = {
    "get_current_datetime": get_current_datetime,
    "calculate": calculate,
}

HARDCODED_TOOLS = [
    {"definition": TOOL_DEF_GET_CURRENT_DATETIME, "handler": get_current_datetime},
    {"definition": TOOL_DEF_CALCULATE, "handler": calculate},
]

# OpenAI-style tools list for get_reply(messages, tools=...)
HARDCODED_TOOLS_DEFINITIONS = [t["definition"] for t in HARDCODED_TOOLS]

MAX_ITERATIONS = 5
TOOL_TIMEOUT_SECONDS = 10.0


async def _run_one_tool(name: str, arguments: dict) -> str:
    """Execute one tool by name with given arguments. Returns result string or error message."""
    handler = HARDCODED_TOOL_HANDLERS.get(name)
    if not handler:
        return f"Error: unknown tool '{name}'."
    try:
        result = await asyncio.wait_for(
            _invoke_handler(handler, arguments),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
        return str(result) if result is not None else ""
    except asyncio.TimeoutError:
        return f"Error: tool '{name}' timed out after {TOOL_TIMEOUT_SECONDS}s."
    except Exception as e:
        logger.exception("Tool %s failed: %s", name, e)
        return f"Error: {e!s}"


async def _invoke_handler(handler: Callable[..., Any], arguments: dict) -> Any:
    """Call handler with arguments; support async and sync."""
    if asyncio.iscoroutinefunction(handler):
        return await handler(**arguments)
    return await asyncio.to_thread(handler, **arguments)


def _tool_result_message_openai(tool_call_id: str, content: str) -> dict:
    """OpenAI format: role=tool, tool_call_id, content."""
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def _append_tool_results_openai(messages: List[dict], tool_calls: List[ToolCall], results: List[str]) -> None:
    """Append assistant message with tool_calls and tool result messages (OpenAI format)."""
    # Assistant message with tool_calls (OpenAI format)
    tool_calls_payload = [
        {
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.name, "arguments": __import__("json").dumps(tc.arguments)},
        }
        for tc in tool_calls
    ]
    # Build content for assistant: empty or text if any
    content = ""
    messages.append({
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls_payload,
    })
    for tc, result in zip(tool_calls, results):
        messages.append(_tool_result_message_openai(tc.id, result))


async def get_reply_with_tools(
    messages: List[dict],
    max_iterations: int = MAX_ITERATIONS,
) -> str:
    """
    Get reply from LLM with tool-calling loop. Uses HARDCODED_TOOLS.
    If no tools or LLM returns text, returns that text. On max_iterations returns fallback message.
    """
    tools_defs = HARDCODED_TOOLS_DEFINITIONS
    if not tools_defs:
        content, _ = await get_reply(messages)
        return content or ""

    iteration = 0
    current_messages = list(messages)

    while iteration < max_iterations:
        iteration += 1
        content, tool_calls = await get_reply(
            current_messages,
            tools=tools_defs,
            tool_choice="auto",
        )

        if tool_calls:
            logger.info("Tool calls: %s", [tc.name for tc in tool_calls])
            results = []
            for tc in tool_calls:
                result = await _run_one_tool(tc.name, tc.arguments or {})
                results.append(result)
            _append_tool_results_openai(current_messages, tool_calls, results)
            continue

        if content:
            return content

        # No content and no tool_calls — should not happen often
        return "Could not complete the operation."

    return "Could not complete the operation."


def get_system_prompt_for_tools() -> str:
    """Return system prompt for tool-calling: from DB if set, else default."""
    try:
        from api.settings_repository import get_llm_settings
        settings = get_llm_settings()
        if settings and (settings.get("system_prompt") or "").strip():
            return (settings.get("system_prompt") or "").strip()
    except Exception:
        pass
    return DEFAULT_SYSTEM_PROMPT_WITH_TOOLS
