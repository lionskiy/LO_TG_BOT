"""Load configuration from environment."""
import os
from pathlib import Path
from typing import Any, Optional, Tuple

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Provider keys and models (whichever block is set in .env is used)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Order of check: first provider with key set wins
_PROVIDERS: Tuple[Tuple[str, bool, str, dict], ...] = (
    ("openai", bool(OPENAI_API_KEY), OPENAI_MODEL, {"api_key": OPENAI_API_KEY}),
    ("anthropic", bool(ANTHROPIC_API_KEY), ANTHROPIC_MODEL, {"api_key": ANTHROPIC_API_KEY}),
    ("google", bool(GOOGLE_API_KEY), GOOGLE_MODEL, {"api_key": GOOGLE_API_KEY}),
    ("groq", bool(GROQ_API_KEY), GROQ_MODEL, {"api_key": GROQ_API_KEY, "base_url": "https://api.groq.com/openai/v1"}),
    (
        "openrouter",
        bool(OPENROUTER_API_KEY),
        OPENROUTER_MODEL,
        {"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL},
    ),
    (
        "azure",
        bool(AZURE_OPENAI_API_KEY) and bool(AZURE_OPENAI_ENDPOINT),
        AZURE_OPENAI_MODEL,
        {
            "api_key": AZURE_OPENAI_API_KEY,
            "azure_endpoint": (AZURE_OPENAI_ENDPOINT or "").rstrip("/"),
            "api_version": AZURE_OPENAI_API_VERSION,
        },
    ),
    (
        "ollama",
        "OLLAMA_BASE_URL" in os.environ or "OLLAMA_MODEL" in os.environ,
        OLLAMA_MODEL,
        {"base_url": f"{OLLAMA_BASE_URL.rstrip('/')}/v1", "api_key": "ollama"},
    ),
)

_cached_llm: Optional[Tuple[str, str, dict]] = None


def get_active_llm() -> Tuple[str, str, dict]:
    """Return (provider_name, model, kwargs) for the first provider that has credentials set."""
    global _cached_llm
    if _cached_llm is not None:
        return _cached_llm
    for name, active, model, kwargs in _PROVIDERS:
        if name == "ollama":
            # Ollama: consider active if base_url is set (no key required)
            if OLLAMA_BASE_URL and model:
                _cached_llm = (name, model, kwargs)
                return _cached_llm
            continue
        if active and model and kwargs.get("api_key"):
            _cached_llm = (name, model, kwargs)
            return _cached_llm
    raise ValueError(
        "No LLM provider configured. Set one block in .env (e.g. OPENAI_API_KEY and OPENAI_MODEL)."
    )


def validate_config() -> None:
    """Raise ValueError if required env vars are missing."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set. Check .env or environment.")
    get_active_llm()
