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


def fetch_models_from_api(base_url: str, api_key: str, timeout: float = 15.0) -> tuple[list[dict[str, Any]], str | None]:
    """
    Fetch model list from OpenAI-compatible GET /models.
    Returns (list of {"id": "model-id"}, error_message or None).
    """
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return [], "Base URL is empty"
    url = f"{base}/models"
    headers = {}
    if (api_key or "").strip() and (api_key or "").strip() != "ollama":
        headers["Authorization"] = f"Bearer {(api_key or '').strip()}"
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, headers=headers or None)
    except Exception as e:
        logger.warning("Fetch models request failed: %s", e)
        return [], str(e)
    if r.status_code != 200:
        try:
            data = r.json()
            msg = data.get("error", {}).get("message", data.get("message", r.text))
        except Exception:
            msg = r.text or f"HTTP {r.status_code}"
        return [], msg or f"HTTP {r.status_code}"
    try:
        data = r.json()
        raw = data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        return [], f"Invalid response: {e}"
    # Prefer id; some APIs use "id" in list of models
    models = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        mid = item.get("id") or item.get("model") or ""
        if mid and isinstance(mid, str):
            models.append({"id": mid.strip()})
    return models, None
