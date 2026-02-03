# Текущая реализация приложения LO_TG_BOT

Документ фиксирует состояние приложения на момент создания ветки для работ по экрану «Основные настройки приложения» (Admin panel).

---

## 1. Назначение приложения

Telegram-бот с подключённым LLM для общения в чате. Пользователь пишет сообщения боту; бот отправляет их выбранному LLM-провайдеру и возвращает ответ в тот же чат.

---

## 2. Стек и окружение

- **Язык:** Python 3.10+
- **Зависимости:** см. `requirements.txt`
  - `python-telegram-bot==21.7` — Telegram Bot API (long polling)
  - `openai==1.55.0`, `httpx>=0.27,<0.28` — OpenAI-совместимые клиенты
  - `anthropic`, `google-generativeai` — Anthropic, Google Gemini
  - `python-dotenv` — загрузка `.env`
  - `pytest`, `pytest-asyncio` — тесты
- **Конфигурация:** переменные окружения через `.env` (образец — `.env.example`). Никакой БД и админ-панели в текущей реализации нет.

---

## 3. Структура проекта

```
LO_TG_BOT/
├── main.py                 # Точка входа: логирование, single instance, запуск polling
├── bot/
│   ├── __init__.py
│   ├── config.py           # Загрузка .env, определение активного LLM, валидация
│   ├── llm.py              # Диспетчер LLM: один активный провайдер, get_reply()
│   ├── single_instance.py  # Один экземпляр бота: .bot.pid, завершение предыдущего
│   └── telegram_bot.py     # Обработчики /start и текста, история чата, run_polling()
├── tests/
│   ├── test_config.py
│   └── test_llm.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

---

## 4. Модули и ответственность

### 4.1 `main.py`

- Настройка логирования: уровень из `LOG_LEVEL`, опционально файл `LOG_FILE`, приглушение логов `telegram`, `httpx`, `httpcore`, `openai`.
- Вызов `ensure_single_instance()` и `register_cleanup()` перед запуском бота.
- Запуск `run_polling()` (блокирующий).

### 4.2 `bot/config.py`

- Загрузка `.env` из корня проекта.
- Константы: `BOT_TOKEN`, `LOG_LEVEL`, `LOG_FILE`, ключи и модели для OpenAI, Anthropic, Google, Groq, OpenRouter, Azure, Ollama.
- **Активный LLM:** первый провайдер с заданным ключом (и при необходимости моделью). Результат кэшируется в `_cached_llm`.
- `get_active_llm()` → `(provider_name, model, kwargs)`.
- `validate_config()` — проверяет наличие `BOT_TOKEN` и активного LLM; при ошибке выбрасывает `ValueError`.

### 4.3 `bot/llm.py`

- Один активный провайдер берётся из `get_active_llm()`.
- Обработчики по провайдерам: OpenAI, Groq, OpenRouter, Ollama (через OpenAI-совместимый API), Azure (`OpenAzureOpenAI`), Anthropic, Google (Gemini).
- `get_reply(messages: List[dict])` — асинхронно возвращает текстовый ответ. Системный промпт задаётся в `telegram_bot.py` (константа `SYSTEM_PROMPT`), не из конфига/БД.

### 4.4 `bot/telegram_bot.py`

- Сборка приложения: `Application.builder().token(BOT_TOKEN)`, обработчики `/start` и текстовых сообщений, глобальный error handler (в т.ч. для `Conflict` при нескольких экземплярах).
- История диалога: по `chat_id`, последние 20 пар user/assistant в `_chat_history`.
- Для каждого текстового сообщения: формирование списка сообщений (system + history + user), вызов `get_reply()`, отправка ответа, обновление истории.
- Ошибки LLM преобразуются в короткие сообщения пользователю (`_llm_error_message`), полные детали пишутся в лог.
- `run_polling()` — `app.run_polling(drop_pending_updates=True)`.

### 4.5 `bot/single_instance.py`

- Файл `.bot.pid` в корне проекта хранит PID текущего процесса.
- `ensure_single_instance()`: при старте читает PID, при необходимости завершает старый процесс (SIGTERM, затем SIGKILL), записывает свой PID.
- `register_cleanup()`: при выходе (atexit, SIGTERM, SIGINT) удаляет `.bot.pid`.

---

## 5. Конфигурация (.env)

- **Обязательно:** `BOT_TOKEN` — токен от BotFather.
- **LLM:** используется один блок — первый с заданным ключом. Варианты: OpenAI, Anthropic, Google, Groq, OpenRouter, Azure, Ollama (для Ollama ключ не обязателен, задаётся base URL и модель).
- Опционально: `LOG_LEVEL`, `LOG_FILE`.

Модель и ключи задаются только в `.env`; смена провайдера/модели требует правки `.env` и перезапуска приложения.

---

## 6. Запуск

- **Локально:** `python main.py` (рекомендуется виртуальное окружение и `pip install -r requirements.txt`).
- **Docker:** `docker compose up --build` (или `-d` для фона). Один экземпляр на один токен — и локально, и в Docker не должно быть двух ботов с одним `BOT_TOKEN`.

---

## 7. Ограничения текущей реализации

- Нет веб-интерфейса и админ-панели.
- Нет БД: настройки только в `.env`.
- Нет API для проверки подключения Telegram/LLM и смены настроек «на лету».
- Системный промпт зашит в коде (`SYSTEM_PROMPT` в `telegram_bot.py`).
- Смена бота или LLM возможна только через правку `.env` и перезапуск.

---

## 8. Версионирование документа

| Версия | Дата       | Описание                    |
|--------|------------|-----------------------------|
| 1.0    | 2026-02-03 | Первоначальная фиксация     |
