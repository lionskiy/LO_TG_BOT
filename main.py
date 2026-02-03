"""Entry point: run Telegram bot with LLM."""
import asyncio
import logging
import sys

from bot.config import LOG_FILE, LOG_LEVEL
from bot.telegram_bot import run_polling

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _setup_logging() -> None:
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        format=_LOG_FORMAT,
        level=level,
        stream=sys.stdout,
        force=True,
    )
    root = logging.getLogger()
    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(fh)
    # Меньше шума от библиотек при тестировании
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


if __name__ == "__main__":
    _setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting bot (LOG_LEVEL=%s)", LOG_LEVEL)
    asyncio.run(run_polling())
