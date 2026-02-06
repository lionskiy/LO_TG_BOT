"""LLM client: active provider from settings DB (if active) or from config (.env)."""
import logging
import os
from typing import Dict, List, Optional

from bot.config import get_active_llm

logger = logging.getLogger(__name__)


def _get_llm_from_settings_db() -> Optional[tuple]:
    """
    Return (provider, model, kwargs, system_prompt) from active LLM settings in DB, or None.
    system_prompt may be None. Single DB read to avoid duplicate get_llm_settings_decrypted.
    """
    try:
        from api.settings_repository import get_llm_settings_decrypted
        settings = get_llm_settings_decrypted()
    except Exception:
        return None
    if not settings:
        return None
    provider = (settings.get("llm_type") or "").strip().lower()
    model = (settings.get("model_type") or "").strip()
    api_key = settings.get("api_key")
    base_url = (settings.get("base_url") or "").strip()
    if not model:
        return None
    if provider == "azure":
        kwargs = {
            "api_key": api_key or "",
            "base_url": base_url,
            "azure_endpoint": (settings.get("azure_endpoint") or base_url).rstrip("/"),
            "api_version": (settings.get("api_version") or "2024-02-15-preview").strip(),
        }
    else:
        kwargs = {"api_key": api_key or "", "base_url": base_url}
        if provider in ("openrouter", "deepseek"):
            kwargs["timeout"] = 120.0
    system_prompt = (settings.get("system_prompt") or "").strip() or None
    return (provider, model, kwargs, system_prompt)

# Lazy clients per provider (anthropic, google — config-driven; openai-compatible built per-call for hot-swap)
_anthropic_client: Optional[object] = None
_google_model = None


def _needs_max_completion_tokens(model: str) -> bool:
    """
    Check if model requires max_completion_tokens instead of max_tokens.
    New OpenAI models (gpt-5, o3, o4 series) use max_completion_tokens.
    """
    model_lower = model.lower()
    # GPT-5 series
    if model_lower.startswith("gpt-5") or "gpt-5" in model_lower:
        return True
    # O-series reasoning models
    if model_lower.startswith("o3") or model_lower.startswith("o4"):
        return True
    # O1 series (older reasoning)
    if model_lower.startswith("o1"):
        return True
    return False


async def _reply_openai(messages: List[dict], model: str, kwargs: dict) -> str:
    """
    OpenAI-compatible: always create client from kwargs so DB/config hot-swap uses current api_key and base_url.
    For new models (gpt-5, o3, o4) uses max_completion_tokens; older models use max_tokens.
    """
    from openai import AsyncOpenAI

    base_url = kwargs.get("base_url")
    api_key = kwargs.get("api_key") or ""
    timeout = kwargs.get("timeout")
    client_kw: dict = {}
    if timeout is not None:
        client_kw["timeout"] = float(timeout)
    if base_url:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, **client_kw)
    else:
        client = AsyncOpenAI(api_key=api_key, **client_kw)
    
    # New models require max_completion_tokens; older models use max_tokens
    if _needs_max_completion_tokens(model):
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_completion_tokens=1024
        )
    else:
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_tokens=1024
        )
    return (resp.choices[0].message.content or "").strip()


async def _reply_groq(messages: List[dict], model: str, kwargs: dict) -> str:
    """Groq uses OpenAI-compatible API; new OpenAI models need max_completion_tokens."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"])
    if _needs_max_completion_tokens(model):
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_completion_tokens=1024
        )
    else:
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_tokens=1024
        )
    return (resp.choices[0].message.content or "").strip()


async def _reply_openrouter(messages: List[dict], model: str, kwargs: dict) -> str:
    """OpenRouter uses OpenAI-compatible API; new OpenAI models need max_completion_tokens."""
    from openai import AsyncOpenAI

    # OpenRouter/DeepSeek могут отвечать долго — увеличиваем таймаут
    timeout = kwargs.get("timeout", 120.0)
    client = AsyncOpenAI(
        api_key=kwargs["api_key"],
        base_url=kwargs["base_url"],
        timeout=timeout,
    )
    if _needs_max_completion_tokens(model):
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_completion_tokens=1024
        )
    else:
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_tokens=1024
        )
    return (resp.choices[0].message.content or "").strip()


async def _reply_ollama(messages: List[dict], model: str, kwargs: dict) -> str:
    """Ollama uses OpenAI-compatible API; typically uses max_tokens (local models)."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"])
    # Ollama models typically don't need max_completion_tokens, but check for OpenAI models routed through Ollama
    if _needs_max_completion_tokens(model):
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_completion_tokens=1024
        )
    else:
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_tokens=1024
        )
    return (resp.choices[0].message.content or "").strip()


async def _reply_azure(messages: List[dict], model: str, kwargs: dict) -> str:
    """Azure OpenAI; new OpenAI models (gpt-5, o3, o4) need max_completion_tokens."""
    from openai import AsyncAzureOpenAI

    endpoint = kwargs.get("azure_endpoint") or (kwargs.get("base_url") or "").rstrip("/")
    version = kwargs.get("api_version") or "2024-02-15-preview"
    client = AsyncAzureOpenAI(
        api_key=kwargs.get("api_key") or "",
        azure_endpoint=endpoint,
        api_version=version,
    )
    if _needs_max_completion_tokens(model):
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_completion_tokens=1024
        )
    else:
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


async def _reply_yandex(messages: List[dict], model: str, kwargs: dict) -> str:
    """Yandex GPT: POST .../completion with modelUri (gpt://folder_id/model/latest). Folder from YANDEX_FOLDER_ID."""
    import httpx

    base = (kwargs.get("base_url") or "").strip().rstrip("/")
    api_key = (kwargs.get("api_key") or "").strip()
    if not base or not api_key:
        raise ValueError("Yandex: base_url and api_key required")
    folder_id = os.getenv("YANDEX_FOLDER_ID", "").strip()
    if model.startswith("gpt://"):
        model_uri = model
    elif folder_id:
        model_uri = f"gpt://{folder_id}/{model}/latest"
    else:
        raise ValueError(
            "Yandex: set YANDEX_FOLDER_ID in env or use full model_uri (gpt://folder_id/model/latest) in model field"
        )
    yandex_messages = []
    for m in messages:
        if m.get("role") == "system":
            continue
        role = "user" if m.get("role") == "user" else "assistant"
        yandex_messages.append({"role": role, "text": (m.get("content") or "").strip()})
    if not yandex_messages or yandex_messages[-1]["role"] != "user":
        raise ValueError("Yandex: last message must be from user")
    payload = {
        "modelUri": model_uri,
        "messages": yandex_messages,
        "completionOptions": {"maxTokens": 1024},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{base}/completion",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    if r.status_code != 200:
        try:
            err = r.json()
            msg = err.get("error", {}).get("message", err.get("message", r.text))
        except Exception:
            msg = r.text or f"HTTP {r.status_code}"
        raise RuntimeError(msg or f"HTTP {r.status_code}")
    data = r.json()
    result = (data.get("result") or {}) if isinstance(data, dict) else {}
    alternatives = result.get("alternatives") or []
    if not alternatives:
        return ""
    return (alternatives[0].get("message", {}).get("text") or "").strip()


_HANDLERS: Dict[str, object] = {
    "openai": _reply_openai,
    "groq": _reply_groq,
    "openrouter": _reply_openrouter,
    "ollama": _reply_ollama,
    "azure": _reply_azure,
    "anthropic": _reply_anthropic,
    "google": _reply_google,
    "perplexity": _reply_openai,
    "xai": _reply_openai,
    "deepseek": _reply_openai,
    "yandex": _reply_yandex,
    "custom": _reply_openai,
}


async def get_reply(messages: List[dict]) -> str:
    """Use active LLM from settings DB if present, else from config (.env)."""
    from_db = _get_llm_from_settings_db()
    if from_db:
        provider, model, kwargs, system_prompt = from_db
        if system_prompt:
            new_messages = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") != "system":
                    new_messages.append(m)
            messages = new_messages
    else:
        provider, model, kwargs = get_active_llm()
    logger.info(
        "LLM request provider=%s model=%s messages=%d",
        provider,
        model,
        len(messages),
    )
    handler = _HANDLERS.get(provider)
    if not handler:
        raise ValueError(f"Unknown LLM provider: {provider}")
    reply = await handler(messages, model, kwargs)
    logger.info("LLM response len=%d", len(reply))
    logger.debug("LLM response preview=%s", (reply[:150] + "..." if len(reply) > 150 else reply))
    return reply
