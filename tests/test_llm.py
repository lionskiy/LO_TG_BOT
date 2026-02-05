"""Tests for bot.llm."""
from unittest.mock import AsyncMock, patch

import pytest

from bot import llm


@pytest.mark.asyncio
async def test_get_reply_returns_content():
    with patch.object(llm, "get_active_llm", return_value=("openai", "gpt-4o-mini", {"api_key": "sk-test"})):
        mock_openai = AsyncMock(return_value="Hello from model")
        with patch.dict(llm._HANDLERS, {"openai": mock_openai}):
            result = await llm.get_reply([{"role": "user", "content": "Hi"}])
    assert result == "Hello from model"
    mock_openai.assert_called_once()
    call_args = mock_openai.call_args[0]
    assert call_args[1] == "gpt-4o-mini"
    assert call_args[2]["api_key"] == "sk-test"


@pytest.mark.asyncio
async def test_get_reply_strips_whitespace():
    with patch.object(llm, "get_active_llm", return_value=("openai", "gpt-4o-mini", {"api_key": "sk-test"})):
        with patch.dict(llm._HANDLERS, {"openai": AsyncMock(return_value="answer")}):
            result = await llm.get_reply([{"role": "user", "content": "Hi"}])
    assert result == "answer"


@pytest.mark.asyncio
async def test_get_reply_empty_content_returns_empty_string():
    with patch.object(llm, "get_active_llm", return_value=("openai", "gpt-4o-mini", {"api_key": "sk-test"})):
        with patch.dict(llm._HANDLERS, {"openai": AsyncMock(return_value="")}):
            result = await llm.get_reply([{"role": "user", "content": "Hi"}])
    assert result == ""


@pytest.mark.asyncio
async def test_get_reply_uses_active_provider_and_model():
    with patch.object(
        llm,
        "get_active_llm",
        return_value=("groq", "llama-3.3-70b", {"api_key": "grok", "base_url": "https://api.groq.com/openai/v1"}),
    ):
        mock_groq = AsyncMock(return_value="Groq reply")
        with patch.dict(llm._HANDLERS, {"groq": mock_groq}):
            result = await llm.get_reply([{"role": "user", "content": "Hi"}])
    assert result == "Groq reply"
    mock_groq.assert_called_once()
    call_args = mock_groq.call_args[0]
    assert call_args[1] == "llama-3.3-70b"
    assert call_args[2]["api_key"] == "grok"
