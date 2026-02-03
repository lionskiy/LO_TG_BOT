"""FastAPI application for admin settings API."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db import init_db
from api.settings_repository import get_llm_settings, get_telegram_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    init_db()
    yield
    # Shutdown: nothing to close for SQLite in-process


app = FastAPI(title="LO_TG_BOT Admin API", lifespan=lifespan)


@app.get("/api/settings")
def get_settings():
    """Return all settings (Telegram and LLM). Secrets are masked (last 5 chars)."""
    return {
        "telegram": get_telegram_settings(),
        "llm": get_llm_settings(),
    }
