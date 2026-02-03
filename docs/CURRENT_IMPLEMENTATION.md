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
- **Конфигурация:** переменные окружения через `.env` (образец — `.env.example`). Для админ-панели используется SQLite (или `DATABASE_URL`), секреты шифруются (Fernet, ключ в `SETTINGS_ENCRYPTION_KEY`).

---

## 3. Структура проекта

```
LO_TG_BOT/
├── main.py                     # Точка входа: только бот, настройки из .env
├── run_bot_from_settings.py    # Запуск бота из настроек БД (подпроцесс API)
├── bot/
│   ├── config.py               # .env, активный LLM (fallback при отсутствии БД)
│   ├── llm.py                  # get_reply(): приоритет — БД, затем .env
│   ├── single_instance.py      # .bot.pid, один экземпляр
│   └── telegram_bot.py         # Обработчики, run_polling(), run_polling_with_token()
├── api/
│   ├── app.py                  # FastAPI: /api/settings*, раздача admin/
│   ├── db.py                   # SQLAlchemy, модели TelegramSettingsModel, LLMSettingsModel
│   ├── encryption.py           # Fernet: шифрование токенов/ключей для БД
│   ├── settings_repository.py   # CRUD настроек, маскирование для API
│   ├── bot_runner.py           # Запуск/остановка подпроцесса run_bot_from_settings.py
│   ├── telegram_test.py        # Проверка Telegram getMe
│   ├── llm_test.py             # Проверка подключения к LLM
│   └── llm_providers.py        # Список провайдеров и моделей
├── admin/
│   ├── index.html              # Админ-панель: блоки Telegram и LLM
│   ├── styles.css
│   └── app.js                  # Загрузка/сохранение, Retry, тосты
├── tests/
│   ├── test_config.py
│   ├── test_llm.py
│   └── test_api_settings.py   # Тесты API настроек
├── docs/
│   ├── CURRENT_IMPLEMENTATION.md
│   ├── PLAN - main app settings screen.md
│   └── ACCEPTANCE-PRD-S7.md
├── Dockerfile                  # uvicorn api.app, порт 8000
├── docker-compose.yml          # volume bot_data для data/settings.db
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

- Сначала проверяется наличие активных настроек LLM в БД (`api.settings_repository.get_llm_settings_decrypted`); при наличии используются они (включая системный промпт из БД). Иначе — `get_active_llm()` из `.env`.
- Обработчики по провайдерам: OpenAI, Groq, OpenRouter, Ollama, Azure, Anthropic, Google (Gemini).
- `get_reply(messages: List[dict])` — асинхронно возвращает текстовый ответ.

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

- **Режим «только бот»:** `BOT_TOKEN`, ключи LLM (OpenAI, Anthropic, Google и др.). Опционально: `LOG_LEVEL`, `LOG_FILE`.
- **Режим API + админ-панель:** дополнительно `SETTINGS_ENCRYPTION_KEY` (обязательно для сохранения настроек в БД), при необходимости `DATABASE_URL`, `ADMIN_API_KEY` (опциональная защита эндпоинтов `/api/settings*`).

Настройки из БД (если есть активные) имеют приоритет над `.env` при запуске через uvicorn; бот поднимается подпроцессом с данными из БД.

---

## 6. Запуск

- **Только бот:** `python main.py` — настройки из `.env`.
- **API + админ-панель:** `uvicorn api.app:app --host 0.0.0.0 --port 8000`. Админка: http://localhost:8000/admin/. Бот запускается подпроцессом при наличии активных настроек Telegram в БД.
- **Docker:** `docker compose up --build` — в контейнере работает API + админка (порт 8000), БД в volume `bot_data`. Один экземпляр на один токен.

---

## 7. Реализованные возможности (экран «Основные настройки»)

- Веб-админ-панель: блоки «Телеграм бот» и «LLM» с сохранением в БД (SQLite).
- API настроек: GET/PUT/POST для Telegram и LLM, проверка соединения, активация при успехе.
- Шифрование секретов в БД (Fernet), маскирование в API и на фронте.
- Hot-swap: смена бота и LLM без перезапуска процесса (подпроцесс бота перезапускается при активации новых настроек Telegram; LLM читается из БД при каждом запросе).
- Опциональная авторизация: `ADMIN_API_KEY` и заголовок `X-Admin-Key`.

---

## 8. Версионирование документа

| Версия | Дата       | Описание                    |
|--------|------------|-----------------------------|
| 1.0    | 2026-02-03 | Первоначальная фиксация     |
| 2.0    | 2026-02-03 | Admin API, БД, админ-панель, hot-swap |
