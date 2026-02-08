"""Telegram bot with LLM conversation."""
import asyncio
import logging
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# Max size for HR import file (bytes)
HR_IMPORT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ENABLE_TOOL_CALLING = os.getenv("ENABLE_TOOL_CALLING", "").strip().lower() in ("1", "true", "yes")


def _llm_error_message(exc: Exception) -> str:
    """Краткое сообщение об ошибке LLM для пользователя (без деталей)."""
    exc_msg = str(exc).strip()
    # Всегда логируем тип и текст — в логах видна причина (ключ, модель, таймаут и т.д.)
    logger.error("LLM error type=%s message=%s", type(exc).__name__, exc_msg)
    settings_hint = "Проверьте настройки в админ-панели."
    # 404 / модель не найдена (OpenAI SDK или Anthropic SDK)
    if type(exc).__name__ == "NotFoundError":
        return f"Модель или ресурс не найден. Проверьте имя модели. {settings_hint}"
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
            return f"Ошибка доступа к API: неверный или истёкший API-ключ. {settings_hint}"
        if isinstance(exc, RateLimitError):
            return "Слишком много запросов. Подождите минуту и попробуйте снова."
        if isinstance(exc, (APIConnectionError, APITimeoutError)):
            return "Нет связи с API модели или таймаут. Проверьте интернет и попробуйте позже."
        if isinstance(exc, BadRequestError):
            # OpenAI и др. иногда возвращают 400 с текстом про API key — показываем как ошибку ключа
            lower_msg = exc_msg.lower()
            if "api key" in lower_msg or "incorrect api key" in lower_msg or "invalid api key" in lower_msg:
                return f"Ошибка доступа к API: неверный или истёкший API-ключ. Убедитесь, что выбран правильный провайдер (OpenAI/Anthropic/и т.д.) и ключ от него. {settings_hint}"
            # Текст от API: из body.error.message или str(exc)
            api_detail = exc_msg
            if getattr(exc, "body", None) and isinstance(exc.body, dict):
                err = exc.body.get("error") or exc.body
                if isinstance(err, dict) and err.get("message"):
                    api_detail = str(err.get("message")).strip()
            api_hint = (api_detail[:280] + "…") if len(api_detail) > 280 else api_detail
            return f"Неверный запрос к модели. {api_hint} {settings_hint}"
        if isinstance(exc, NotFoundError):  # openai.NotFoundError
            return f"Модель или ресурс не найден. Проверьте имя модели. {settings_hint}"
        if isinstance(exc, PermissionDeniedError):
            return (
                "Нет доступа к выбранной модели (403). Возможно, ключ не даёт доступ к этой модели "
                f"или нужен другой тариф. Выберите другую модель или проверьте ключ. {settings_hint}"
            )
    except ImportError:
        pass
    return f"Ошибка при обращении к модели ({type(exc).__name__}). {settings_hint} Попробуйте позже."

from telegram import Update
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.config import BOT_TOKEN, validate_config
from bot.llm import get_reply
from bot.tool_calling import get_reply_with_tools, get_system_prompt_for_tools
from tools import execute_tool, load_all_plugins
from tools.models import ToolCall as ToolsToolCall

# Per-chat conversation history for LLM context (last N messages)
MAX_HISTORY_MESSAGES = 20
# Cap total chats to avoid unbounded memory growth
MAX_CHATS_IN_MEMORY = 500
_chat_history: Dict[int, List[dict]] = defaultdict(list)

SYSTEM_PROMPT = (
    "Ты дружелюбный помощник в чате Telegram. "
    "Отвечай кратко и по делу. Общайся на языке пользователя."
)


def _get_messages(chat_id: int, user_text: str, use_tools: bool = False) -> List[dict]:
    """Build message list for API: system + history + new user message."""
    history = _chat_history[chat_id]
    system = get_system_prompt_for_tools() if use_tools else SYSTEM_PROMPT
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


def _append_to_history(chat_id: int, user_content: str, assistant_content: str) -> None:
    """Keep last MAX_HISTORY_MESSAGES in history. Evict oldest chat if over MAX_CHATS_IN_MEMORY."""
    if len(_chat_history) >= MAX_CHATS_IN_MEMORY and chat_id not in _chat_history:
        # Remove one of the oldest (smallest history) chats to make room
        oldest_key = min(_chat_history.keys(), key=lambda k: len(_chat_history[k]))
        del _chat_history[oldest_key]
        logger.debug("evicted chat_id=%s from history (max %d chats)", oldest_key, MAX_CHATS_IN_MEMORY)
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


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document messages: if Excel and from service admin, run HR import; else pass to LLM with text."""
    if not update.message or not update.message.document:
        return
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else 0
    doc = update.message.document
    file_name = (doc.file_name or "").lower()
    if not file_name.endswith(".xlsx") and not file_name.endswith(".xls"):
        await update.message.reply_text(
            "Поддерживаются только файлы Excel (.xlsx, .xls). Для импорта сотрудников отправьте файл с листами ДДЖ и Инфоком."
        )
        return
    if doc.file_size and doc.file_size > HR_IMPORT_MAX_FILE_SIZE:
        await update.message.reply_text(f"Файл слишком большой (макс. {HR_IMPORT_MAX_FILE_SIZE // (1024*1024)} МБ).")
        return
    if not is_service_admin(user_id):
        await update.message.reply_text("Импорт сотрудников доступен только сервисным администраторам.")
        return
    await update.message.chat.send_action("typing")
    tmp_path = None
    try:
        tg_file = await context.bot.get_file(doc.file_id)
        suffix = Path(file_name).suffix or ".xlsx"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="hr_import_")
        os.close(fd)
        await tg_file.download_to_drive(tmp_path)
        await load_all_plugins()
        tc = ToolsToolCall(
            id="hr_import",
            name="hr",
            arguments={"action": "import_employees", "file_path": tmp_path},
        )
        result = await execute_tool(tc, telegram_id=user_id)
        if result.success:
            text = result.content
            if isinstance(text, str) and text.startswith("{"):
                import json
                try:
                    data = json.loads(text)
                    added = data.get("added_count", 0)
                    names = data.get("added_names", [])
                    errs = data.get("errors", [])
                    msg = f"Импорт выполнен. Добавлено сотрудников: {added}."
                    if names:
                        msg += " Фамилии: " + ", ".join(names[:10])
                    if errs:
                        msg += f" Ошибки при обработке: {len(errs)}."
                    text = msg
                except Exception:
                    pass
            await update.message.reply_text(text[:4000] if len(text) > 4000 else text)
        else:
            await update.message.reply_text(result.content or "Ошибка импорта.")
    except Exception as e:
        logger.exception("HR document import failed: %s", e)
        await update.message.reply_text("Ошибка при обработке файла. Попробуйте позже.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.debug("Cleanup temp file %s: %s", tmp_path, e)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages: send to LLM and reply."""
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_id = update.effective_user.id if update.effective_user else None
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

    use_tools = ENABLE_TOOL_CALLING
    messages = _get_messages(chat_id, user_text, use_tools=use_tools)
    typing_task = None
    typing_stop = asyncio.Event()

    async def _typing_loop() -> None:
        while not typing_stop.is_set():
            try:
                await update.message.chat.send_action("typing")
            except Exception:
                break
            try:
                await asyncio.wait_for(typing_stop.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

    try:
        typing_task = asyncio.create_task(_typing_loop())
        if use_tools:
            try:
                reply = await get_reply_with_tools(messages, telegram_id=user_id)
            except Exception as e:
                logger.warning("Tool-calling failed, falling back to plain reply: %s", e)
                content, _ = await get_reply(messages)
                reply = content or ""
        else:
            content, _ = await get_reply(messages)
            reply = content or ""
    except Exception as e:
        logger.exception("LLM request failed: %s", e)
        user_msg = _llm_error_message(e)
        await update.message.reply_text(user_msg)
        return
    finally:
        typing_stop.set()
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass

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
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(_error_handler)
    return app


def build_application_with_token(token: str) -> Application:
    """Create application with given token (for hot-swap from settings DB)."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
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


def is_service_admin(telegram_id: int) -> bool:
    """
    Check if telegram_id is a service admin.
    Ready for future use in bot handlers (admin commands, etc.).
    Not used in current handlers (future functionality).
    """
    try:
        from api.service_admins_repository import is_service_admin as check_admin
        return check_admin(telegram_id)
    except Exception as e:
        logger.debug("is_service_admin check failed: %s", e)
        return False
