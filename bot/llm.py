"""LLM client: one active provider from config, model from env."""
from typing import Dict, List, Optional

from bot.config import get_active_llm

# Lazy clients per provider (openai-compatible and others)
_openai_client: Optional[object] = None
_anthropic_client: Optional[object] = None
_google_model = None


async def _reply_openai(messages: List[dict], model: str, kwargs: dict) -> str:
    from openai import AsyncOpenAI

    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=kwargs["api_key"])
    resp = await _openai_client.chat.completions.create(
        model=model, messages=messages, max_tokens=1024
    )
    return (resp.choices[0].message.content or "").strip()


async def _reply_groq(messages: List[dict], model: str, kwargs: dict) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"])
    resp = await client.chat.completions.create(
        model=model, messages=messages, max_tokens=1024
    )
    return (resp.choices[0].message.content or "").strip()


async def _reply_openrouter(messages: List[dict], model: str, kwargs: dict) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"])
    resp = await client.chat.completions.create(
        model=model, messages=messages, max_tokens=1024
    )
    return (resp.choices[0].message.content or "").strip()


async def _reply_ollama(messages: List[dict], model: str, kwargs: dict) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"])
    resp = await client.chat.completions.create(
        model=model, messages=messages, max_tokens=1024
    )
    return (resp.choices[0].message.content or "").strip()


async def _reply_azure(messages: List[dict], model: str, kwargs: dict) -> str:
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        api_key=kwargs["api_key"],
        azure_endpoint=kwargs["azure_endpoint"],
        api_version=kwargs["api_version"],
    )
    resp = await client.chat.completions.create(
        model=model, messages=messages, max_tokens=1024
    )
    return (resp.choices[0].message.content or "").strip()


async def _reply_anthropic(messages: List[dict], model: str, kwargs: dict) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=kwargs["api_key"])
    system = next((m["content"] for m in messages if m.get("role") == "system"), "") or ""
    msgs = [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
        for m in messages
        if m.get("role") != "system"
    ]
    resp = await client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=msgs,
    )
    return (resp.content[0].text if resp.content else "").strip()


async def _reply_google(messages: List[dict], model: str, kwargs: dict) -> str:
    import google.generativeai as genai

    genai.configure(api_key=kwargs["api_key"])
    gemini = genai.GenerativeModel(model)
    system = next((m["content"] for m in messages if m.get("role") == "system"), None)
    parts = []
    if system:
        parts.append(system)
    for m in messages:
        if m.get("role") == "system":
            continue
        parts.append(f"{m['role']}: {m['content']}")
    parts.append("assistant:")
    prompt = "\n\n".join(parts)
    resp = await gemini.generate_content_async(prompt)
    return (resp.text or "").strip()


_HANDLERS: Dict[str, object] = {
    "openai": _reply_openai,
    "groq": _reply_groq,
    "openrouter": _reply_openrouter,
    "ollama": _reply_ollama,
    "azure": _reply_azure,
    "anthropic": _reply_anthropic,
    "google": _reply_google,
}


async def get_reply(messages: List[dict]) -> str:
    """Use the active LLM provider and its model from config."""
    provider, model, kwargs = get_active_llm()
    handler = _HANDLERS.get(provider)
    if not handler:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return await handler(messages, model, kwargs)
