"""Tests for bot.llm."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot import llm


@pytest.mark.asyncio
async def test_get_reply_returns_content():
    fake_response = MagicMock()
    fake_response.choices = [
        MagicMock(message=MagicMock(content="Hello from model"))
    ]
    with patch.object(llm, "_get_client") as get_client:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=fake_response)
        get_client.return_value = client

        result = await llm.get_reply([{"role": "user", "content": "Hi"}])

    assert result == "Hello from model"
    client.chat.completions.create.assert_called_once()
    call_messages = client.chat.completions.create.call_args[1]["messages"]
    assert call_messages == [{"role": "user", "content": "Hi"}]


@pytest.mark.asyncio
async def test_get_reply_strips_whitespace():
    fake_response = MagicMock()
    fake_response.choices = [
        MagicMock(message=MagicMock(content="  answer  \n"))
    ]
    with patch.object(llm, "_get_client") as get_client:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=fake_response)
        get_client.return_value = client

        result = await llm.get_reply([{"role": "user", "content": "Hi"}])

    assert result == "answer"


@pytest.mark.asyncio
async def test_get_reply_empty_content_returns_empty_string():
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content=None))]
    with patch.object(llm, "_get_client") as get_client:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=fake_response)
        get_client.return_value = client

        result = await llm.get_reply([{"role": "user", "content": "Hi"}])

    assert result == ""
