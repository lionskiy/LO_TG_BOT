"""LLM provider defaults (base URLs, model lists) for settings API."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# LLM type (id) -> default base URL. Custom has no default (user must enter).
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "google_nano_banana": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "xai": "https://api.x.ai/v1",
    "perplexity": "https://api.perplexity.ai",
    "deepseek": "https://api.deepseek.com",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "azure": "https://your-resource.openai.azure.com/",
    "custom": "",
}

# For GET /api/settings/llm/providers: id, name, defaultBaseUrl, models.standard, models.reasoning
PROVIDERS_LIST = [
    {
        "id": "openai",
        "name": "Open AI",
        "defaultBaseUrl": DEFAULT_BASE_URLS["openai"],
        "models": {
            "standard": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-3.5-turbo"],
            "reasoning": ["o3", "o3-mini", "o3-pro", "o4-mini", "gpt-5.2", "gpt-5-mini", "gpt-5-nano", "gpt-5"],
        },
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "defaultBaseUrl": DEFAULT_BASE_URLS["anthropic"],
        "models": {
            "standard": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-3.5-sonnet"],
            "reasoning": ["claude-3.5-sonnet"],
        },
    },
    {
        "id": "google",
        "name": "Google Gemini",
        "defaultBaseUrl": DEFAULT_BASE_URLS["google"],
        "models": {
            "standard": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3-flash"],
            "reasoning": ["gemini-2.5-pro", "gemini-3-pro", "gemini-3-deep-think"],
        },
    },
    {
        "id": "google_nano_banana",
        "name": "Google Nano Banana",
        "defaultBaseUrl": DEFAULT_BASE_URLS["google_nano_banana"],
        "models": {"standard": ["gemini-2.5-flash-image", "gemini-3-pro-image"], "reasoning": []},
    },
    {
        "id": "xai",
        "name": "xAI (Grok)",
        "defaultBaseUrl": DEFAULT_BASE_URLS["xai"],
        "models": {"standard": ["grok-3", "grok-2"], "reasoning": ["grok-4", "grok-4-reasoning"]},
    },
    {
        "id": "perplexity",
        "name": "Perplexity",
        "defaultBaseUrl": DEFAULT_BASE_URLS["perplexity"],
        "models": {
            "standard": ["sonar", "sonar-pro"],
            "reasoning": ["sonar-reasoning", "sonar-reasoning-pro", "sonar-deep-research"],
        },
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "defaultBaseUrl": DEFAULT_BASE_URLS["deepseek"],
        "models": {"standard": ["deepseek-chat", "deepseek-coder"], "reasoning": ["deepseek-reasoner"]},
    },
    {
        "id": "azure",
        "name": "Azure OpenAI",
        "defaultBaseUrl": DEFAULT_BASE_URLS["azure"],
        "models": {
            "standard": ["gpt-4o", "gpt-4o-mini", "gpt-35-turbo", "gpt-4"],
            "reasoning": [],
        },
    },
    {
        "id": "custom",
        "name": "Custom",
        "defaultBaseUrl": "",
        "models": {"standard": [], "reasoning": []},
    },
]


def get_default_base_url(llm_type: str) -> str:
    """Return default base URL for provider; empty for custom/unknown."""
    key = (llm_type or "").strip().lower().replace(" ", "_")
    return DEFAULT_BASE_URLS.get(key, "")


# OpenAI: API часто возвращает только модели, доступные ключу. Добавляем известные id, чтобы в списке были и o1/o3/gpt-5.
OPENAI_KNOWN_MODEL_IDS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-3.5-turbo",
    "o1", "o1-mini", "o3", "o3-mini", "o3-pro", "o4-mini",
    "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5.2",
]


def fetch_models_from_api(base_url: str, api_key: str, timeout: float = 15.0) -> tuple[list[dict[str, Any]], str | None]:
    """
    Fetch full model list from OpenAI-compatible GET /models.
    Follows pagination (has_more + after or last_id) when present so all models are returned.
    Returns (list of {"id": "model-id"}, error_message or None).
    """
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return [], "Base URL is empty"
    headers: dict[str, str] = {}
    if (api_key or "").strip() and (api_key or "").strip() != "ollama":
        headers["Authorization"] = f"Bearer {(api_key or '').strip()}"
    all_models: list[dict[str, Any]] = []
    after: str | None = None
    max_pages = 50
    page = 0
    try:
        with httpx.Client(timeout=timeout) as client:
            while page < max_pages:
                page += 1
                url = f"{base}/models"
                params: dict[str, str] = {}
                if after:
                    params["after"] = after
                r = client.get(url, headers=headers or None, params=params or None)
                if r.status_code != 200:
                    if page == 1:
                        try:
                            data = r.json()
                            msg = data.get("error", {}).get("message", data.get("message", r.text))
                        except Exception:
                            msg = r.text or f"HTTP {r.status_code}"
                        return [], msg or f"HTTP {r.status_code}"
                    break
                try:
                    data = r.json()
                except Exception as e:
                    if page == 1:
                        return [], f"Invalid response: {e}"
                    break
                raw = data.get("data", []) if isinstance(data, dict) else []
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    mid = item.get("id") or item.get("model") or ""
                    if mid and isinstance(mid, str):
                        mid = mid.strip()
                        display = (item.get("display_name") or item.get("name") or "").strip() or None
                        all_models.append({"id": mid, "display_name": display})
                has_more = data.get("has_more") if isinstance(data, dict) else False
                last_id = data.get("last_id") if isinstance(data, dict) else None
                if has_more and raw:
                    after = last_id or (raw[-1].get("id") or raw[-1].get("model") if isinstance(raw[-1], dict) else None)
                    if isinstance(after, str):
                        after = after.strip()
                    else:
                        after = None
                if not has_more or not after:
                    break
        return all_models, None
    except Exception as e:
        logger.warning("Fetch models request failed: %s", e)
        return [], str(e)


def fetch_models_anthropic(api_key: str, timeout: float = 15.0) -> tuple[list[dict[str, Any]], str | None]:
    """
    Fetch model list from Anthropic GET /v1/models.
    Returns (list of {"id": "...", "display_name": "..."}, error_message or None).
    """
    key = (api_key or "").strip()
    if not key:
        return [], "API key is empty"
    base = "https://api.anthropic.com"
    url = f"{base}/v1/models"
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    all_models: list[dict[str, Any]] = []
    after_id: str | None = None
    max_pages = 50
    page = 0
    try:
        with httpx.Client(timeout=timeout) as client:
            while page < max_pages:
                page += 1
                params: dict[str, str] = {}
                if after_id:
                    params["after_id"] = after_id
                r = client.get(url, headers=headers, params=params or None)
                if r.status_code != 200:
                    if page == 1:
                        try:
                            data = r.json()
                            msg = data.get("error", {}).get("message", data.get("message", r.text))
                        except Exception:
                            msg = r.text or f"HTTP {r.status_code}"
                        return [], msg or f"HTTP {r.status_code}"
                    break
                try:
                    data = r.json()
                except Exception as e:
                    if page == 1:
                        return [], f"Invalid response: {e}"
                    break
                raw = data.get("data", []) if isinstance(data, dict) else []
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    mid = item.get("id") or ""
                    if mid and isinstance(mid, str):
                        mid = mid.strip()
                        display = (item.get("display_name") or "").strip() or None
                        all_models.append({"id": mid, "display_name": display})
                has_more = data.get("has_more") if isinstance(data, dict) else False
                last_id = data.get("last_id") if isinstance(data, dict) else None
                if has_more and last_id:
                    after_id = last_id
                else:
                    break
        return all_models, None
    except Exception as e:
        logger.warning("Anthropic fetch models failed: %s", e)
        return [], str(e)
