"""Telegram bot with LLM conversation."""
import logging
from collections import defaultdict
from typing import Dict, List

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.config import BOT_TOKEN, validate_config
from bot.llm import get_reply

logger = logging.getLogger(__name__)

# Per-chat conversation history for LLM context (last N messages)
MAX_HISTORY_MESSAGES = 20
_chat_history: Dict[int, List[dict]] = defaultdict(list)

SYSTEM_PROMPT = (
    "Ты дружелюбный помощник в чате Telegram. "
    "Отвечай кратко и по делу. Общайся на языке пользователя."
)


def _get_messages(chat_id: int, user_text: str) -> List[dict]:
    """Build message list for API: system + history + new user message."""
    history = _chat_history[chat_id]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


def _append_to_history(chat_id: int, user_content: str, assistant_content: str) -> None:
    """Keep last MAX_HISTORY_MESSAGES in history."""
    history = _chat_history[chat_id]
    history.append({"role": "user", "content": user_content})
    history.append({"role": "assistant", "content": assistant_content})
    if len(history) > MAX_HISTORY_MESSAGES:
        _chat_history[chat_id] = history[-MAX_HISTORY_MESSAGES:]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("command /start chat_id=%s user_id=%s", chat_id, user_id)
    await update.message.reply_text(
        "Привет! Я бот с LLM. Напиши мне что угодно — я постараюсь ответить."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages: send to LLM and reply."""
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_text = update.message.text.strip()
    if not user_text:
        return

    history_len = len(_chat_history[chat_id])
    logger.info(
        "message chat_id=%s len=%d history_messages=%d",
        chat_id,
        len(user_text),
        history_len,
    )
    logger.debug("message chat_id=%s text=%s", chat_id, user_text[:200])

    await update.message.chat.send_action("typing")
    messages = _get_messages(chat_id, user_text)
    try:
        reply = await get_reply(messages)
    except Exception as e:
        logger.exception("LLM request failed: %s", e)
        await update.message.reply_text(
            "Произошла ошибка при обращении к модели. Попробуй позже."
        )
        return

    if reply:
        _append_to_history(chat_id, user_text, reply)
        logger.info("reply sent chat_id=%s reply_len=%d", chat_id, len(reply))
        logger.debug("reply chat_id=%s text=%s", chat_id, reply[:200])
        await update.message.reply_text(reply)
    else:
        logger.warning("empty reply chat_id=%s", chat_id)
        await update.message.reply_text("Не удалось получить ответ. Попробуй ещё раз.")


def build_application() -> Application:
    """Create and configure the Telegram application."""
    logger.info("Building application, validating config")
    validate_config()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


async def run_polling() -> None:
    """Run bot with long polling."""
    app = build_application()
    await app.initialize()
    await app.start()
    logger.info("Bot started, polling (drop_pending_updates=True)")
    await app.updater.start_polling(drop_pending_updates=True)
    await app.updater.idle()
    logger.info("Polling idle ended, shutting down")
    await app.stop()
    await app.shutdown()
