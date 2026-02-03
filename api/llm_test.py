"""Test LLM provider connection (minimal API call)."""
import logging
from typing import Tuple

import httpx

from api.db import CONNECTION_STATUS_FAILED, CONNECTION_STATUS_SUCCESS
from api.settings_repository import (
    get_llm_credentials_for_test,
    update_llm_connection_status,
)

logger = logging.getLogger(__name__)


def _test_openai_compatible(creds: dict) -> Tuple[bool, str]:
    """GET /models for OpenAI-compatible (openai, groq, openrouter, ollama, etc.)."""
    base = (creds.get("base_url") or "").strip().rstrip("/")
    key = (creds.get("api_key") or "").strip()
    if not base:
        return False, "Base URL is empty"
    url = f"{base}/models"
    headers = {}
    if key and key != "ollama":
        headers["Authorization"] = f"Bearer {key}"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=headers or None)
    except Exception as e:
        logger.warning("LLM models request failed: %s", e)
        return False, str(e)
    if r.status_code == 200:
        return True, "Connection tested successfully"
    try:
        data = r.json()
        msg = data.get("error", {}).get("message", data.get("message", r.text))
    except Exception:
        msg = r.text or f"HTTP {r.status_code}"
    return False, msg or f"HTTP {r.status_code}"


def _test_anthropic(creds: dict) -> Tuple[bool, str]:
    """Minimal Anthropic messages API call."""
    try:
        import anthropic
    except ImportError:
        return False, "anthropic package not installed"
    key = (creds.get("api_key") or "").strip()
    if not key:
        return False, "API key is empty"
    try:
        client = anthropic.Anthropic(api_key=key)
        client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return True, "Connection tested successfully"
    except anthropic.APIStatusError as e:
        return False, e.message or str(e)
    except Exception as e:
        logger.warning("Anthropic test failed: %s", e)
        return False, str(e)


def _test_google(creds: dict) -> Tuple[bool, str]:
    """Minimal Google Generative AI call."""
    try:
        import google.generativeai as genai
    except ImportError:
        return False, "google-generativeai package not installed"
    key = (creds.get("api_key") or "").strip()
    if not key:
        return False, "API key is empty"
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        model.generate_content("Hi")
        return True, "Connection tested successfully"
    except Exception as e:
        logger.warning("Google genai test failed: %s", e)
        return False, str(e)


def test_llm_connection() -> Tuple[str, str]:
    """
    Run provider-specific test. Update DB status and return (status, message).
    status is CONNECTION_STATUS_SUCCESS, CONNECTION_STATUS_FAILED, or 'not_configured'.
    """
    creds = get_llm_credentials_for_test()
    if not creds:
        update_llm_connection_status("not_configured")
        return ("not_configured", "API key not configured")

    llm_type = (creds.get("llm_type") or "").strip().lower()
    ok, message = False, ""
    if llm_type == "anthropic":
        ok, message = _test_anthropic(creds)
    elif llm_type == "google":
        ok, message = _test_google(creds)
    else:
        # openai, groq, openrouter, ollama, azure, custom, etc.
        ok, message = _test_openai_compatible(creds)

    status = CONNECTION_STATUS_SUCCESS if ok else CONNECTION_STATUS_FAILED
    update_llm_connection_status(status)
    return (status, message)
