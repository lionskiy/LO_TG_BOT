"""Tests for bot.tool_calling: hardcoded tools and get_reply_with_tools."""
from unittest.mock import AsyncMock, patch

import pytest

from bot.tool_calling import (
    HARDCODED_TOOLS_DEFINITIONS,
    calculate,
    get_current_datetime,
    get_reply_with_tools,
    get_system_prompt_for_tools,
)


@pytest.mark.asyncio
async def test_get_current_datetime_returns_valid_format():
    result = await get_current_datetime()
    assert result
    assert "(" in result and ")" in result
    # Should contain weekday and time-like pattern
    assert any(day in result for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))


@pytest.mark.asyncio
async def test_calculate_basic_operations():
    assert await calculate("2 + 2") == "4"
    assert await calculate("10 - 3") == "7"
    assert await calculate("4 * 5") == "20"
    assert await calculate("20 / 4") == "5.0"


@pytest.mark.asyncio
async def test_calculate_with_functions():
    result = await calculate("sqrt(16)")
    assert result in ("4", "4.0") or float(result) == 4
    result = await calculate("sin(0) + cos(0)")
    assert "1" in result  # 1 or 1.0


@pytest.mark.asyncio
async def test_calculate_handles_errors():
    result = await calculate("1/0")
    assert "Error" in result or "error" in result.lower()
    result = await calculate("abc")
    assert "Error" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_calculate_safe_from_injection():
    # Attempts to run code should not execute
    result = await calculate("__import__('os').system('id')")
    assert "Error" in result or "error" in result.lower() or "NameNotDefined" in result


def test_hardcoded_tools_definitions():
    assert len(HARDCODED_TOOLS_DEFINITIONS) >= 2
    names = [t["function"]["name"] for t in HARDCODED_TOOLS_DEFINITIONS]
    assert "get_current_datetime" in names
    assert "calculate" in names


@pytest.mark.asyncio
async def test_get_reply_with_tools_no_tool_call():
    """When LLM returns text only, get_reply_with_tools returns that text."""
    with patch("bot.tool_calling.get_reply", new_callable=AsyncMock, return_value=("Hello, user!", None)):
        result = await get_reply_with_tools([{"role": "user", "content": "Hi"}])
    assert result == "Hello, user!"


@pytest.mark.asyncio
async def test_get_reply_with_tools_single_tool_call():
    """LLM returns tool_calls; we execute and get final text."""
    from bot.llm import ToolCall

    with patch("bot.tool_calling.get_reply", new_callable=AsyncMock) as mock_get_reply:
        mock_get_reply.side_effect = [
            (None, [ToolCall(id="call_1", name="get_current_datetime", arguments={})]),
            ("Сейчас 2024-01-15 12:00:00 (Monday).", None),
        ]
        result = await get_reply_with_tools([{"role": "user", "content": "What time is it?"}])
    assert "2024" in result or "12:00" in result or "Monday" in result or "Сейчас" in result
    assert mock_get_reply.call_count >= 2


@pytest.mark.asyncio
async def test_get_reply_with_tools_max_iterations():
    """When LLM keeps returning tool_calls, we stop at max_iterations."""
    from bot.llm import ToolCall

    with patch("bot.tool_calling.get_reply", new_callable=AsyncMock, return_value=(None, [ToolCall(id="x", name="get_current_datetime", arguments={})])):
        result = await get_reply_with_tools([{"role": "user", "content": "Hi"}], max_iterations=2)
    assert result == "Could not complete the operation."


def test_get_system_prompt_for_tools_returns_string():
    prompt = get_system_prompt_for_tools()
    assert isinstance(prompt, str)
    assert "Russian" in prompt or "tool" in prompt.lower()
