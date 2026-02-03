"""Telegram bot with LLM conversation."""
import logging
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)


def _llm_error_message(exc: Exception) -> str:
    """Краткое сообщение об ошибке LLM для пользователя (без деталей)."""
    # Всегда логируем тип и текст — видно при любом LOG_LEVEL
    logger.error("LLM error type=%s message=%s", type(exc).__name__, str(exc))
    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            NotFoundError,
            PermissionDeniedError,
            RateLimitError,
        )
        if isinstance(exc, AuthenticationError):
            return "Ошибка доступа к API: проверьте API-ключ в .env (неверный или истёкший)."
        if isinstance(exc, RateLimitError):
            return "Слишком много запросов. Подождите минуту и попробуйте снова."
        if isinstance(exc, (APIConnectionError, APITimeoutError)):
            return "Нет связи с API модели или таймаут. Проверьте интернет и попробуйте позже."
        if isinstance(exc, BadRequestError):
            return "Неверный запрос к модели (например, неверное имя модели в .env). Проверьте OPENAI_MODEL и попробуйте снова."
        if isinstance(exc, NotFoundError):
            return "Модель или ресурс не найден. Проверьте имя модели в .env (OPENAI_MODEL)."
        if isinstance(exc, PermissionDeniedError):
            return "Нет доступа к модели или API. Проверьте ключ и права доступа в .env."
    except ImportError:
        pass
    return f"Ошибка при обращении к модели ({type(exc).__name__}). Проверьте .env и логи. Попробуйте позже."

from telegram import Update
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.config import BOT_TOKEN, validate_config
from bot.llm import get_reply

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
        user_msg = _llm_error_message(e)
        await update.message.reply_text(user_msg)
        return

    if reply:
        _append_to_history(chat_id, user_text, reply)
        logger.info("reply sent chat_id=%s reply_len=%d", chat_id, len(reply))
        logger.debug("reply chat_id=%s text=%s", chat_id, reply[:200])
        await update.message.reply_text(reply)
    else:
        logger.warning("empty reply chat_id=%s", chat_id)
        await update.message.reply_text("Не удалось получить ответ. Попробуй ещё раз.")


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логируем ошибки; для Conflict — явная подсказка про один экземпляр."""
    exc = context.error
    if isinstance(exc, Conflict):
        logger.error(
            "Conflict: запущено несколько экземпляров бота с одним токеном. "
            "Остановите все кроме одного (docker compose down ИЛИ завершите python main.py)."
        )
    else:
        logger.exception("Update %s caused error: %s", update, exc)


def build_application() -> Application:
    """Create and configure the Telegram application (token from config)."""
    logger.info("Building application, validating config")
    validate_config()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(_error_handler)
    return app


def build_application_with_token(token: str) -> Application:
    """Create application with given token (for hot-swap from settings DB)."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(_error_handler)
    return app


def run_polling() -> None:
    """Run bot with long polling (blocking until shutdown)."""
    app = build_application()
    logger.info("Starting polling (drop_pending_updates=True)")
    app.run_polling(drop_pending_updates=True)


def run_polling_with_token(token: str) -> None:
    """Run bot with given token (e.g. from settings DB). Blocking."""
    app = build_application_with_token(token)
    logger.info("Starting polling with token from settings (drop_pending_updates=True)")
    app.run_polling(drop_pending_updates=True)
