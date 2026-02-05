"""
Run Telegram bot using active settings from DB (for API-managed hot-swap).
Do not use single_instance here — the API process manages the bot subprocess.
"""
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on path
_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

# Minimal logging for subprocess
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from api.db import init_db
from api.settings_repository import get_telegram_settings_decrypted
from bot.telegram_bot import run_polling_with_token


def main() -> None:
    init_db()
    try:
        creds = get_telegram_settings_decrypted()
    except ValueError as e:
        logger.warning("Cannot read Telegram settings (missing or invalid SETTINGS_ENCRYPTION_KEY): %s; exiting", e)
        return
    if not creds or not creds.get("access_token"):
        logger.warning("No active Telegram settings in DB; exiting")
        return
    token = creds["access_token"]
    logger.info("Starting bot from DB settings")
    run_polling_with_token(token)


if __name__ == "__main__":
    main()
