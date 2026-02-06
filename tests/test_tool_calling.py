"""Tests for bot.tool_calling and tools (registry, executor, plugins)."""
from unittest.mock import AsyncMock, patch

import pytest

from bot.tool_calling import (
    get_reply_with_tools,
    get_system_prompt_for_tools,
    MAX_ITERATIONS,
)
from tools import get_registry, load_all_plugins, execute_tool
from tools.models import ToolCall as ToolsToolCall


@pytest.fixture
async def plugins_loaded():
    """Load plugins once for tests that need registry. Set _plugins_loaded so get_reply_with_tools uses it."""
    import bot.tool_calling as tc
    reg = get_registry()
    reg.clear()
    result = await load_all_plugins()
    tc._plugins_loaded = True
    return result


@pytest.mark.asyncio
async def test_get_current_datetime_returns_valid_format(plugins_loaded):
    tc = ToolsToolCall(id="t1", name="get_current_datetime", arguments={})
    result = await execute_tool(tc)
    assert result.success
    assert result.content
    assert "(" in result.content and ")" in result.content
    assert any(
        d in result.content
        for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    )


@pytest.mark.asyncio
async def test_calculate_basic_operations(plugins_loaded):
    tc = ToolsToolCall(id="t1", name="calculate", arguments={"expression": "2 + 2"})
    result = await execute_tool(tc)
    assert result.success
    assert result.content == "4"
    tc2 = ToolsToolCall(id="t2", name="calculate", arguments={"expression": "10 - 3"})
    result2 = await execute_tool(tc2)
    assert result2.success
    assert result2.content == "7"


@pytest.mark.asyncio
async def test_calculate_handles_errors(plugins_loaded):
    tc = ToolsToolCall(id="t1", name="calculate", arguments={"expression": "1/0"})
    result = await execute_tool(tc)
    assert "Error" in result.content or "error" in result.content.lower()


@pytest.mark.asyncio
async def test_registry_has_tools_after_load(plugins_loaded):
    reg = get_registry()
    tools = reg.get_tools_for_llm()
    names = [t["function"]["name"] for t in tools]
    assert "get_current_datetime" in names
    assert "calculate" in names


@pytest.mark.asyncio
async def test_get_reply_with_tools_no_tool_call():
    with patch("bot.tool_calling.get_reply", new_callable=AsyncMock, return_value=("Hello, user!", None)):
        result = await get_reply_with_tools([{"role": "user", "content": "Hi"}])
    assert result == "Hello, user!"


@pytest.mark.asyncio
async def test_get_reply_with_tools_single_tool_call(plugins_loaded):
    from bot.llm import ToolCall as LLMToolCall

    with patch("bot.tool_calling.get_reply", new_callable=AsyncMock) as mock_get_reply:
        mock_get_reply.side_effect = [
            (None, [LLMToolCall(id="call_1", name="get_current_datetime", arguments={})]),
            ("Сейчас 2024-01-15 12:00:00 (Monday).", None),
        ]
        result = await get_reply_with_tools([{"role": "user", "content": "What time is it?"}])
    assert "2024" in result or "12:00" in result or "Monday" in result or "Сейчас" in result
    assert mock_get_reply.call_count >= 2


@pytest.mark.asyncio
async def test_get_reply_with_tools_max_iterations(plugins_loaded):
    from bot.llm import ToolCall as LLMToolCall

    with patch("bot.tool_calling.get_reply", new_callable=AsyncMock, return_value=(
        None, [LLMToolCall(id="x", name="get_current_datetime", arguments={})]
    )):
        result = await get_reply_with_tools([{"role": "user", "content": "Hi"}], max_iterations=2)
    assert result == "Could not complete the operation."


def test_get_system_prompt_for_tools_returns_string():
    prompt = get_system_prompt_for_tools()
    assert isinstance(prompt, str)
    assert "Russian" in prompt or "tool" in prompt.lower()
