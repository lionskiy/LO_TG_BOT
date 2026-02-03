"""Load configuration from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def validate_config() -> None:
    """Raise ValueError if required env vars are missing."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set. Check .env or environment.")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Check .env or environment.")
