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
    "yandex": "https://llm.api.cloud.yandex.net/foundationModels/v1",
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
        "id": "groq",
        "name": "Groq",
        "defaultBaseUrl": DEFAULT_BASE_URLS["groq"],
        "models": {
            "standard": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            "reasoning": ["llama-3.1-70b-reasoning", "llama-3.1-405b-reasoning"],
        },
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "defaultBaseUrl": DEFAULT_BASE_URLS["openrouter"],
        "models": {"standard": ["anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-exp"], "reasoning": []},
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "defaultBaseUrl": DEFAULT_BASE_URLS["ollama"],
        "models": {"standard": ["llama3.2", "mistral", "qwen2.5"], "reasoning": ["deepseek-r1"]},
    },
    {
        "id": "yandex",
        "name": "Yandex GPT",
        "defaultBaseUrl": DEFAULT_BASE_URLS["yandex"],
        "models": {"standard": ["yandexgpt-lite", "yandexgpt"], "reasoning": []},
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
    Fetch full model list from OpenAI-compatible GET /models.
    Handles different response formats and pagination styles.
    Returns (list of {"id": "model-id", "display_name": ...?}, error_message or None).
    """
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return [], "Base URL is empty"
    
    # Detect provider type for optimization
    is_openai = "api.openai.com" in base
    is_groq = "groq.com" in base
    is_openrouter = "openrouter.ai" in base
    
    # Page size: OpenAI supports 100, others vary
    page_size = 100 if is_openai else (50 if (is_groq or is_openrouter) else None)
    
    headers: dict[str, str] = {}
    if (api_key or "").strip() and (api_key or "").strip() != "ollama":
        headers["Authorization"] = f"Bearer {(api_key or '').strip()}"
    
    all_models: list[dict[str, Any]] = []
    seen_ids: set[str] = set()  # Deduplication
    after: str | None = None
    max_pages = 100
    page = 0
    
    try:
        with httpx.Client(timeout=timeout) as client:
            while page < max_pages:
                page += 1
                url = f"{base}/models"
                params: dict[str, str] = {}
                
                # Pagination parameters (different providers use different params)
                if after:
                    params["after"] = after
                elif page > 1:
                    # Some providers use 'offset' or 'page' instead of 'after'
                    # Try 'after' first, fallback handled below
                    pass
                
                # Always include limit if page_size is set to ensure consistent page sizes
                # This prevents pagination issues where later pages return different sizes
                if page_size is not None:
                    params["limit"] = str(page_size)
                
                logger.debug("Fetching models page %d from %s (after=%s, limit=%s)", 
                           page, url, after or "none", params.get("limit") or "none")
                
                try:
                    r = client.get(url, headers=headers if headers else None, params=params if params else None)
                except httpx.TimeoutException:
                    if page == 1:
                        return [], "Request timeout"
                    logger.debug("Page %d timeout, stopping pagination", page)
                    break
                except httpx.RequestError as e:
                    if page == 1:
                        return [], f"Request failed: {e}"
                    logger.debug("Page %d request error, stopping pagination: %s", page, e)
                    break
                
                if r.status_code != 200:
                    if page == 1:
                        try:
                            error_data = r.json()
                            msg = error_data.get("error", {}).get("message", 
                                  error_data.get("message", r.text[:200]))
                        except Exception:
                            msg = r.text[:200] if r.text else f"HTTP {r.status_code}"
                        return [], msg or f"HTTP {r.status_code}"
                    # On later pages, non-200 might mean end of pagination
                    logger.debug("Page %d returned status %d, stopping pagination", page, r.status_code)
                    break
                
                try:
                    data = r.json()
                except Exception as e:
                    if page == 1:
                        return [], f"Invalid JSON response: {e}"
                    logger.debug("Page %d JSON parse failed, stopping pagination: %s", page, e)
                    break
                
                # Handle different response formats
                raw: list[dict[str, Any]] = []
                if isinstance(data, dict):
                    # Standard format: {"data": [...]}
                    raw = data.get("data", [])
                    # Alternative: {"models": [...]} (some providers)
                    if not raw:
                        raw = data.get("models", [])
                    # Alternative: direct list in "result"
                    if not raw and "result" in data:
                        result = data["result"]
                        if isinstance(result, list):
                            raw = result
                elif isinstance(data, list):
                    # Some providers return list directly
                    raw = data
                
                if not isinstance(raw, list):
                    raw = []
                
                # Process models from this page
                page_models_count = 0
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    
                    # Extract model ID (try different field names)
                    mid = (item.get("id") or item.get("model") or 
                          item.get("name") or "").strip()
                    
                    # Clean up model ID (remove "models/" prefix if present)
                    if mid.startswith("models/"):
                        mid = mid[7:].strip()
                    
                    if not mid:
                        continue
                    
                    # Deduplication
                    mid_lower = mid.lower()
                    if mid_lower in seen_ids:
                        continue
                    seen_ids.add(mid_lower)
                    
                    # Extract display name
                    display = (item.get("display_name") or item.get("name") or 
                              item.get("displayName") or "").strip() or None
                    
                    all_models.append({"id": mid, "display_name": display})
                    page_models_count += 1
                
                logger.debug("Page %d: got %d models (total so far: %d)", 
                           page, page_models_count, len(all_models))
                
                # If we got no models and it's not the first page, we're done
                if page_models_count == 0 and page > 1:
                    logger.debug("Page %d returned no models, stopping pagination", page)
                    break
                
                # Check pagination indicators (handle different formats)
                has_more = False
                last_id: str | None = None
                
                if isinstance(data, dict):
                    has_more = data.get("has_more", False)
                    last_id = data.get("last_id") or data.get("lastId")
                    
                    # Some providers use "next" or "nextPageToken"
                    if not has_more and not last_id:
                        next_token = data.get("next") or data.get("nextPageToken")
                        if next_token:
                            has_more = True
                            last_id = next_token
                
                # Get last item ID as fallback
                last_item_id: str | None = None
                if raw and isinstance(raw[-1], dict):
                    last_item_id = (raw[-1].get("id") or raw[-1].get("model") or "").strip()
                
                # Determine next page token
                after = None
                if last_id and isinstance(last_id, str) and last_id.strip():
                    after = last_id.strip()
                elif last_item_id:
                    after = last_item_id
                
                # Decide whether to continue pagination
                should_continue = False
                
                # Explicit has_more flag
                if has_more is True:
                    should_continue = True
                # Got a full page - might be more
                elif page_size is not None and len(raw) >= page_size:
                    should_continue = True
                # Have pagination token
                elif after:
                    should_continue = True
                
                if not should_continue:
                    logger.debug("No more pages (has_more=%s, after=%s, page_size=%d, got=%d)", 
                               has_more, after, page_size or 0, len(raw))
                    break
                    
        logger.info("Fetched %d unique models from %s", len(all_models), base)
        return all_models, None
        
    except Exception as e:
        logger.exception("Fetch models request failed: %s", e)
        return [], f"Unexpected error: {e}"


def fetch_models_google(api_key: str, timeout: float = 15.0) -> tuple[list[dict[str, Any]], str | None]:
    """
    Fetch model list from Google Gemini GET /v1beta/models (key in query).
    Returns (list of {"id": "baseModelId", "display_name": "..."}, error_message or None).
    """
    key = (api_key or "").strip()
    if not key:
        return [], "API key is empty"
    
    base = "https://generativelanguage.googleapis.com"
    url = f"{base}/v1beta/models"
    params: dict[str, str] = {"key": key}
    all_models: list[dict[str, Any]] = []
    seen_ids: set[str] = set()  # Deduplication
    page_token: str | None = None
    max_pages = 50  # Increased limit
    page = 0
    
    try:
        with httpx.Client(timeout=timeout) as client:
            while page < max_pages:
                page += 1
                current_params = params.copy()
                if page_token:
                    current_params["pageToken"] = page_token
                
                logger.debug("Fetching Google models page %d (pageToken=%s)", page, page_token or "none")
                
                try:
                    r = client.get(url, params=current_params)
                except httpx.TimeoutException:
                    if page == 1:
                        return [], "Request timeout"
                    logger.debug("Page %d timeout, stopping pagination", page)
                    break
                except httpx.RequestError as e:
                    if page == 1:
                        return [], f"Request failed: {e}"
                    logger.debug("Page %d request error, stopping pagination: %s", page, e)
                    break
                
                if r.status_code != 200:
                    if page == 1:
                        try:
                            error_data = r.json()
                            msg = error_data.get("error", {}).get("message", 
                                  error_data.get("message", r.text[:200]))
                        except Exception:
                            msg = r.text[:200] if r.text else f"HTTP {r.status_code}"
                        return [], msg or f"HTTP {r.status_code}"
                    logger.debug("Page %d returned status %d, stopping pagination", page, r.status_code)
                    break
                
                try:
                    data = r.json()
                except Exception as e:
                    if page == 1:
                        return [], f"Invalid JSON response: {e}"
                    logger.debug("Page %d JSON parse failed, stopping pagination: %s", page, e)
                    break
                
                raw = data.get("models", []) if isinstance(data, dict) else []
                if not isinstance(raw, list):
                    raw = []
                
                if not raw and page > 1:
                    logger.debug("Page %d returned no models, stopping pagination", page)
                    break
                
                page_models_count = 0
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    
                    # Google uses "baseModelId" or extracts from "name"
                    name = (item.get("name") or "").strip()
                    base_id = (item.get("baseModelId") or "").strip()
                    
                    # Extract model ID
                    mid = base_id
                    if not mid and name:
                        # Remove "models/" prefix if present
                        mid = name.replace("models/", "").strip()
                    
                    if not mid:
                        continue
                    
                    # Deduplication
                    mid_lower = mid.lower()
                    if mid_lower in seen_ids:
                        continue
                    seen_ids.add(mid_lower)
                    
                    display = (item.get("displayName") or "").strip() or None
                    all_models.append({"id": mid, "display_name": display})
                    page_models_count += 1
                
                logger.debug("Page %d: got %d models (total so far: %d)", 
                           page, page_models_count, len(all_models))
                
                page_token = (data.get("nextPageToken") or "").strip() or None
                if not page_token:
                    logger.debug("No nextPageToken, stopping pagination")
                    break
                    
        logger.info("Fetched %d unique models from Google", len(all_models))
        return all_models, None
        
    except Exception as e:
        logger.exception("Google fetch models failed: %s", e)
        return [], f"Unexpected error: {e}"


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
    seen_ids: set[str] = set()  # Deduplication
    after_id: str | None = None
    max_pages = 100
    page = 0
    
    try:
        with httpx.Client(timeout=timeout) as client:
            while page < max_pages:
                page += 1
                params: dict[str, str] = {}
                if after_id:
                    params["after_id"] = after_id
                
                logger.debug("Fetching Anthropic models page %d (after_id=%s)", page, after_id or "none")
                
                try:
                    r = client.get(url, headers=headers, params=params if params else None)
                except httpx.TimeoutException:
                    if page == 1:
                        return [], "Request timeout"
                    logger.debug("Page %d timeout, stopping pagination", page)
                    break
                except httpx.RequestError as e:
                    if page == 1:
                        return [], f"Request failed: {e}"
                    logger.debug("Page %d request error, stopping pagination: %s", page, e)
                    break
                
                if r.status_code != 200:
                    if page == 1:
                        try:
                            error_data = r.json()
                            msg = error_data.get("error", {}).get("message", 
                                  error_data.get("message", r.text[:200]))
                        except Exception:
                            msg = r.text[:200] if r.text else f"HTTP {r.status_code}"
                        return [], msg or f"HTTP {r.status_code}"
                    logger.debug("Page %d returned status %d, stopping pagination", page, r.status_code)
                    break
                
                try:
                    data = r.json()
                except Exception as e:
                    if page == 1:
                        return [], f"Invalid JSON response: {e}"
                    logger.debug("Page %d JSON parse failed, stopping pagination: %s", page, e)
                    break
                
                raw = data.get("data", []) if isinstance(data, dict) else []
                if not isinstance(raw, list):
                    raw = []
                
                if not raw and page > 1:
                    logger.debug("Page %d returned no models, stopping pagination", page)
                    break
                
                page_models_count = 0
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    
                    mid = (item.get("id") or "").strip()
                    if not mid:
                        continue
                    
                    # Deduplication
                    mid_lower = mid.lower()
                    if mid_lower in seen_ids:
                        continue
                    seen_ids.add(mid_lower)
                    
                    display = (item.get("display_name") or "").strip() or None
                    all_models.append({"id": mid, "display_name": display})
                    page_models_count += 1
                
                logger.debug("Page %d: got %d models (total so far: %d)", 
                           page, page_models_count, len(all_models))
                
                # Anthropic pagination
                has_more = data.get("has_more", False) if isinstance(data, dict) else False
                last_id = data.get("last_id") if isinstance(data, dict) else None
                
                if has_more and last_id:
                    after_id = last_id
                else:
                    logger.debug("No more pages (has_more=%s, last_id=%s)", has_more, last_id)
                    break
                    
        logger.info("Fetched %d unique models from Anthropic", len(all_models))
        return all_models, None
        
    except Exception as e:
        logger.exception("Anthropic fetch models failed: %s", e)
        return [], f"Unexpected error: {e}"
