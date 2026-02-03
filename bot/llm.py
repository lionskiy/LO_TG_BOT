"""LLM client for generating replies."""
from typing import List, Optional

from openai import AsyncOpenAI

from bot.config import OPENAI_API_KEY

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


async def get_reply(messages: List[dict]) -> str:
    """
    Get assistant reply from OpenAI Chat API.
    messages: list of {"role": "user"|"assistant"|"system", "content": "..."}
    """
    client = _get_client()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1024,
    )
    choice = response.choices[0]
    return (choice.message.content or "").strip()
