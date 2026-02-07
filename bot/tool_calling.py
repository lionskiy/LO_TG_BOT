"""
Orchestrates tool-calling: loads plugins, gets tools from registry, calls LLM, executes via executor.
"""
import json
import logging
from typing import List

from bot.llm import ToolCall as LLMToolCall, get_reply
from tools import get_registry, load_all_plugins, execute_tool
from tools.models import ToolCall as ToolsToolCall

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

MAX_ITERATIONS = 5

_plugins_loaded = False


async def _ensure_plugins_loaded() -> None:
    global _plugins_loaded
    if not _plugins_loaded:
        result = await load_all_plugins()
        logger.info("Plugins loaded: %s, tools: %d", result.loaded, result.total_tools)
        _plugins_loaded = True


def _tool_result_message_openai(tool_call_id: str, content: str) -> dict:
    """OpenAI format: role=tool, tool_call_id, content."""
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def _append_tool_results_openai(
    messages: List[dict], tool_calls: List[LLMToolCall], results: List[str]
) -> None:
    """Append assistant message with tool_calls and tool result messages (OpenAI format)."""
    tool_calls_payload = [
        {
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments or {})},
        }
        for tc in tool_calls
    ]
    messages.append({
        "role": "assistant",
        "content": "",
        "tool_calls": tool_calls_payload,
    })
    for tc, result in zip(tool_calls, results):
        messages.append(_tool_result_message_openai(tc.id, result))


async def get_reply_with_tools(
    messages: List[dict],
    max_iterations: int = MAX_ITERATIONS,
) -> str:
    """
    Get reply from LLM with tool-calling loop. Uses plugin registry and executor.
    If no tools or LLM returns text, returns that text. On max_iterations returns fallback message.
    """
    await _ensure_plugins_loaded()
    registry = get_registry()
    tools_defs = registry.get_tools_for_llm()
    if not tools_defs:
        content, _ = await get_reply(messages)
        return (content or "") if content else ""

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
            if content:
                current_messages.append({"role": "assistant", "content": content})
            results = []
            for tc in tool_calls:
                tools_tc = ToolsToolCall(id=tc.id, name=tc.name, arguments=tc.arguments or {})
                tr = await execute_tool(tools_tc)
                results.append(tr.content)
            _append_tool_results_openai(current_messages, tool_calls, results)
            continue

        if content:
            return content

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
