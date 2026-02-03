"""Entry point: run Telegram bot with LLM."""
import asyncio
import logging

from bot.telegram_bot import run_polling

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)

if __name__ == "__main__":
    asyncio.run(run_polling())
