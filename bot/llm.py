"""LLM client: active provider from settings DB (if active) or from config (.env)."""
import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from bot.config import get_active_llm

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Single tool call from LLM. Phase 2 will move to tools/models.py."""
    id: str
    name: str
    arguments: dict


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
    Check if OpenAI-compatible model requires max_completion_tokens instead of max_tokens.
    
    Applies to OpenAI-compatible providers (OpenAI, Groq, OpenRouter, Ollama, Azure, etc.):
    - New OpenAI models (gpt-5, o3, o4 series) require max_completion_tokens
    - Older models (gpt-4, gpt-3.5, etc.) use max_tokens
    
    Does NOT apply to:
    - Anthropic (uses max_tokens)
    - Google Gemini (uses max_output_tokens)
    - Yandex GPT (uses maxTokens)
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


def _parse_openai_tool_calls(message) -> List[ToolCall]:
    """Parse OpenAI response message.tool_calls into List[ToolCall]."""
    tool_calls = getattr(message, "tool_calls", None) or []
    result = []
    for tc in tool_calls:
        fid = getattr(tc, "id", None) or ""
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", None) or ""
        args_str = getattr(fn, "arguments", None) or "{}"
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
        except json.JSONDecodeError:
            args = {}
        result.append(ToolCall(id=fid, name=name, arguments=args))
    return result


async def _reply_openai(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """
    OpenAI: always create client from kwargs so DB/config hot-swap uses current api_key and base_url.
    For new models (gpt-5, o3, o4) uses max_completion_tokens; older models use max_tokens.
    With tools: returns (content, tool_calls or None).
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

    create_kw: dict = {}
    if _needs_max_completion_tokens(model):
        create_kw["max_completion_tokens"] = 1024
    else:
        create_kw["max_tokens"] = 1024
    if tools:
        create_kw["tools"] = tools
        create_kw["tool_choice"] = tool_choice

    resp = await client.chat.completions.create(
        model=model, messages=messages, **create_kw
    )
    msg = resp.choices[0].message
    content = (msg.content or "").strip() or None
    parsed = _parse_openai_tool_calls(msg)
    if parsed:
        return (content, parsed)
    return (content if content else None, None)


async def _reply_groq(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """Groq: OpenAI-compatible API; supports tools like OpenAI."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"])
    create_kw: dict = {}
    if _needs_max_completion_tokens(model):
        create_kw["max_completion_tokens"] = 1024
    else:
        create_kw["max_tokens"] = 1024
    if tools:
        create_kw["tools"] = tools
        create_kw["tool_choice"] = tool_choice
    resp = await client.chat.completions.create(model=model, messages=messages, **create_kw)
    msg = resp.choices[0].message
    content = (msg.content or "").strip() or None
    parsed = _parse_openai_tool_calls(msg)
    if parsed:
        return (content, parsed)
    return (content, None)


async def _reply_openrouter(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """OpenRouter: OpenAI-compatible API; supports tools like OpenAI."""
    from openai import AsyncOpenAI

    timeout = kwargs.get("timeout", 120.0)
    client = AsyncOpenAI(
        api_key=kwargs["api_key"], base_url=kwargs["base_url"], timeout=timeout,
    )
    create_kw: dict = {}
    if _needs_max_completion_tokens(model):
        create_kw["max_completion_tokens"] = 1024
    else:
        create_kw["max_tokens"] = 1024
    if tools:
        create_kw["tools"] = tools
        create_kw["tool_choice"] = tool_choice
    resp = await client.chat.completions.create(model=model, messages=messages, **create_kw)
    msg = resp.choices[0].message
    content = (msg.content or "").strip() or None
    parsed = _parse_openai_tool_calls(msg)
    if parsed:
        return (content, parsed)
    return (content, None)


async def _reply_ollama(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """Ollama: OpenAI-compatible; supports tools when provided."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"])
    create_kw: dict = {}
    if _needs_max_completion_tokens(model):
        create_kw["max_completion_tokens"] = 1024
    else:
        create_kw["max_tokens"] = 1024
    if tools:
        create_kw["tools"] = tools
        create_kw["tool_choice"] = tool_choice
    resp = await client.chat.completions.create(model=model, messages=messages, **create_kw)
    msg = resp.choices[0].message
    content = (msg.content or "").strip() or None
    parsed = _parse_openai_tool_calls(msg)
    if parsed:
        return (content, parsed)
    return (content, None)


async def _reply_azure(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """Azure OpenAI: OpenAI-compatible; supports tools like OpenAI."""
    from openai import AsyncAzureOpenAI

    endpoint = kwargs.get("azure_endpoint") or (kwargs.get("base_url") or "").rstrip("/")
    version = kwargs.get("api_version") or "2024-02-15-preview"
    client = AsyncAzureOpenAI(
        api_key=kwargs.get("api_key") or "",
        azure_endpoint=endpoint,
        api_version=version,
    )
    create_kw: dict = {}
    if _needs_max_completion_tokens(model):
        create_kw["max_completion_tokens"] = 1024
    else:
        create_kw["max_tokens"] = 1024
    if tools:
        create_kw["tools"] = tools
        create_kw["tool_choice"] = tool_choice
    resp = await client.chat.completions.create(model=model, messages=messages, **create_kw)
    msg = resp.choices[0].message
    content = (msg.content or "").strip() or None
    parsed = _parse_openai_tool_calls(msg)
    if parsed:
        return (content, parsed)
    return (content, None)


def _parse_anthropic_tool_calls(content_blocks) -> List[ToolCall]:
    """Parse Anthropic response content blocks (tool_use) into List[ToolCall]."""
    result = []
    for block in content_blocks or []:
        if getattr(block, "type", None) != "tool_use":
            continue
        tid = getattr(block, "id", None) or ""
        name = getattr(block, "name", None) or ""
        inp = getattr(block, "input", None)
        if isinstance(inp, dict):
            args = inp
        else:
            try:
                args = json.loads(inp) if inp else {}
            except (TypeError, json.JSONDecodeError):
                args = {}
        result.append(ToolCall(id=tid, name=name, arguments=args))
    return result


async def _reply_anthropic(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """
    Anthropic Claude: uses max_tokens. With tools, passes tools in request and parses tool_use blocks.
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=kwargs["api_key"])
    system = next((m["content"] for m in messages if m.get("role") == "system"), "") or ""
    msgs = [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
        for m in messages
        if m.get("role") != "system"
    ]
    create_kw: dict = {"model": model, "max_tokens": 1024, "system": system, "messages": msgs}
    if tools:
        # Anthropic format: list of {"name", "description", "input_schema"}
        anthropic_tools = []
        for t in tools:
            fn = t.get("function") or {}
            anthropic_tools.append({
                "name": fn.get("name", ""),
                "description": fn.get("description") or "",
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            })
        create_kw["tools"] = anthropic_tools
        create_kw["tool_choice"] = "auto" if tool_choice == "auto" else tool_choice
    resp = await client.messages.create(**create_kw)
    text_part = ""
    for block in (resp.content or []):
        if getattr(block, "type", None) == "text":
            text_part += getattr(block, "text", "") or ""
    content = text_part.strip() or None
    tool_calls = _parse_anthropic_tool_calls(resp.content)
    if tool_calls:
        return (content, tool_calls)
    return (content, None)


def _parse_google_tool_calls(candidates) -> List[ToolCall]:
    """Parse Gemini response candidates for function_call parts into List[ToolCall]."""
    result = []
    for cand in (candidates or []):
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            fc = getattr(part, "function_call", None)
            if not fc:
                continue
            name = getattr(fc, "name", None) or ""
            args = getattr(fc, "args", None) or {}
            if isinstance(args, dict):
                pass
            else:
                args = dict(args) if args else {}
            # Gemini may not give id; generate one for consistency
            result.append(ToolCall(id=f"gc_{name}_{len(result)}", name=name, arguments=args))
    return result


async def _reply_google(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """
    Google Gemini: uses max_output_tokens. With tools, uses generate_content with tools and parses function_call.
    """
    import google.generativeai as genai

    genai.configure(api_key=kwargs["api_key"])
    config = {"max_output_tokens": 1024}
    if tools:
        # Convert OpenAI-style tools to Gemini function declarations
        from google.generativeai.types import Tool, FunctionDeclaration
        declarations = []
        for t in tools:
            fn = t.get("function") or {}
            name = fn.get("name", "")
            desc = fn.get("description") or ""
            params = fn.get("parameters") or {}
            declarations.append(FunctionDeclaration(name=name, description=desc, parameters=params))
        tool = Tool(function_declarations=declarations)
        # Gemini 2.x generate_content with tools returns response with function_call in parts
        model_obj = genai.GenerativeModel(model, generation_config=config, tools=[tool])
    else:
        model_obj = genai.GenerativeModel(model, generation_config=config)
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
    resp = await model_obj.generate_content_async(prompt)
    text_part = (resp.text or "").strip() or None
    tool_calls = _parse_google_tool_calls(getattr(resp, "candidates", None))
    if tool_calls:
        return (text_part, tool_calls)
    return (text_part, None)


async def _reply_yandex(
    messages: List[dict], model: str, kwargs: dict,
    tools: Optional[List[dict]] = None, tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """
    Yandex GPT: uses maxTokens in completionOptions (not max_tokens).
    POST .../completion with modelUri (gpt://folder_id/model/latest). Folder from YANDEX_FOLDER_ID.
    """
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
        return (None, None)
    text = (alternatives[0].get("message", {}).get("text") or "").strip()
    return (text or None, None)


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


async def get_reply(
    messages: List[dict],
    tools: Optional[List[dict]] = None,
    tool_choice: str = "auto",
) -> Tuple[Optional[str], Optional[List[ToolCall]]]:
    """
    Use active LLM from settings DB if present, else from config (.env).
    Returns (content, tool_calls). When tools=None, always (content, None). When tools provided,
    returns (content, None) for text reply or (None, tool_calls) when LLM requested tool use.
    """
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
        "LLM request provider=%s model=%s messages=%d tools=%s",
        provider, model, len(messages), bool(tools),
    )
    handler = _HANDLERS.get(provider)
    if not handler:
        raise ValueError(f"Unknown LLM provider: {provider}")
    content, tool_calls = await handler(messages, model, kwargs, tools=tools, tool_choice=tool_choice)
    if content:
        logger.info("LLM response len=%d", len(content))
        logger.debug("LLM response preview=%s", (content[:150] + "..." if len(content) > 150 else content))
    if tool_calls:
        logger.info("LLM tool_calls count=%d", len(tool_calls))
    return (content, tool_calls)
