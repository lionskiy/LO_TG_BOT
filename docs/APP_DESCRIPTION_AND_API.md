# LO_TG_BOT: описание приложения и API

Документ описывает, как работает приложение, какие внешние API используются и как взаимодействовать с приложением по API.

---

## 1. Назначение приложения

**LO_TG_BOT** — Telegram-бот с подключённым LLM (большая языковая модель). Пользователь общается с ботом в Telegram; бот отправляет сообщения выбранному LLM-провайдеру и возвращает ответ в тот же чат.

Поддерживаются два режима работы:

- **Только бот** — запуск `python main.py`, настройки из `.env`.
- **API + админ-панель** — запуск `uvicorn api.app:app` (или Docker); настройки хранятся в БД, веб-интерфейс для управления, бот поднимается подпроцессом при наличии активных настроек Telegram.

---

## 2. Архитектура и поток данных

### 2.1 Общая схема

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LO_TG_BOT (ваше приложение)                      │
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────┐     ┌────────────────┐ │
│  │  Telegram Bot     │     │  Admin FastAPI    │     │  SQLite (БД)    │ │
│  │  (long polling)   │     │  :8000            │     │  settings.db    │ │
│  │  run_bot_*.py     │     │  /api/settings*   │     │  (секреты       │ │
│  │  или main.py      │     │  /admin/          │     │   шифруются)    │ │
│  └────────┬─────────┘     └────────┬──────────┘     └────────┬────────┘ │
│           │                        │                          │          │
│           │                        └──────────────────────────┘          │
│           │                                     чтение/запись настроек    │
│           │                                                                 │
│           ▼                                                                 │
│  ┌──────────────────┐                                                      │
│  │  bot/llm.py      │  get_reply(messages) → вызов активного LLM           │
│  │  (приоритет: БД  │                                                      │
│  │   затем .env)    │                                                      │
│  └────────┬─────────┘                                                      │
└───────────┼───────────────────────────────────────────────────────────────┘
            │
            │ Исходящие запросы (см. раздел 3)
            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  Внешний мир                                                               │
│  • Telegram Bot API (api.telegram.org или свой base_url)                   │
│  • LLM-провайдеры: OpenAI, Anthropic, Google, Groq, OpenRouter,           │
│    Ollama, Azure, Yandex GPT, Perplexity, xAI, DeepSeek, custom            │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Как обрабатывается сообщение пользователя

1. Пользователь отправляет боту текстовое сообщение в Telegram.
2. Бот (библиотека `python-telegram-bot`) получает обновление через **long polling** — процесс сам периодически опрашивает Telegram API (`getUpdates`), входящих HTTP-запросов от Telegram к вашему серверу нет.
3. Обработчик собирает контекст: системный промпт (из БД или дефолтный), последние 20 пар user/assistant по этому чату, новое сообщение пользователя.
4. Вызывается `get_reply(messages)` в `bot/llm.py`:
   - Сначала проверяется наличие активных настроек LLM в БД (`api.settings_repository.get_llm_settings_decrypted`).
   - Если есть — используются провайдер, модель, API-ключ и системный промпт из БД.
   - Если нет — используется конфиг из `.env` (`bot.config.get_active_llm`).
5. Выполняется HTTP-запрос к выбранному LLM-провайдеру (см. раздел 3.2).
6. Ответ LLM отправляется пользователю в тот же чат через Telegram Bot API; история диалога обновляется.

### 2.3 Режимы запуска бота

| Режим | Как запускается | Откуда настройки |
|-------|------------------|-------------------|
| Только бот | `python main.py` | Только `.env` (BOT_TOKEN, ключи LLM) |
| API + админка | `uvicorn api.app:app --host 0.0.0.0 --port 8000` или Docker | БД (при старте приложения поднимается подпроцесс `run_bot_from_settings.py`, который читает Telegram-токен и настройки LLM из БД) |

В режиме API при сохранении/активации настроек Telegram подпроцесс бота перезапускается (`api.bot_runner.restart_bot`). Смена LLM происходит без перезапуска — настройки читаются из БД при каждом запросе к `get_reply`.

---

## 3. Внешние API (исходящие, «смотрящие наружу»)

Приложение **само инициирует** запросы к внешним сервисам. Входящих вызовов от внешнего мира к боту (кроме Admin API, см. раздел 4) нет.

### 3.1 Telegram Bot API

- **Назначение:** получение обновлений (сообщений пользователей) и отправка ответов.
- **Кто инициирует:** приложение (long polling).
- **Куда:** по умолчанию `https://api.telegram.org`; в настройках админки можно указать свой **Base URL** (например, для работы через прокси или локный MTProto-прокси).
- **Основные вызовы:**
  - `getUpdates` — опрос новых сообщений (long polling).
  - `sendMessage` — отправка ответа в чат.
  - `getMe` — проверка токена (при сохранении настроек Telegram и при «Проверить соединение» в админке).

Никакой входящий webhook от Telegram к вашему серверу не настраивается — используется только long polling (исходящие запросы с вашего сервера к Telegram).

### 3.2 LLM-провайдеры (исходящие HTTP/HTTPS)

Бот обращается к одному выбранному провайдеру за ответом. Все вызовы **исходящие** с вашего сервера к API провайдера.

| Провайдер | Тип запроса | Назначение |
|-----------|--------------|------------|
| **OpenAI** | POST к `base_url` (часто `https://api.openai.com/v1`) | Chat Completions |
| **Anthropic** | Собственный API (anthropic SDK) | Claude (messages.create) |
| **Google** | Google Generative AI (Gemini) | generate_content_async |
| **Groq, OpenRouter, Ollama, Perplexity, xAI, DeepSeek, Custom** | OpenAI-совместимый POST (chat completions) | Единый формат запросов |
| **Azure** | Azure OpenAI endpoint | Chat Completions |
| **Yandex GPT** | POST к Yandex Foundation Models API | completion |

Дополнительно админка при «Загрузить модели» может вызывать:

- **OpenAI-совместимый** GET `/models` (по `base_url`);
- **Google** GET `https://generativelanguage.googleapis.com/v1beta/models`;
- **Anthropic** GET `https://api.anthropic.com/v1/models`.

Итог: все обращения к LLM и к Telegram — **исходящие** с вашего приложения; никакой внешний сервис не «стучится» в бота для доставки сообщений или ответов LLM.

---

## 4. Взаимодействие с приложением по API (входящее API)

Единственный способ программно взаимодействовать с приложением извне — **Admin API** (FastAPI), доступный при запуске через `uvicorn api.app:app` (или Docker).

### 4.1 Базовые сведения

- **Базовый URL:** например `http://localhost:8000` (порт задаётся при запуске uvicorn).
- **Документация OpenAPI:** при запущенном приложении — `http://localhost:8000/docs` (Swagger UI).
- **Защита:** если в `.env` задан `ADMIN_API_KEY`, все запросы к эндпоинтам ниже должны содержать заголовок:  
  `X-Admin-Key: <значение ADMIN_API_KEY>`.  
  Иначе возвращается 403.

### 4.2 Эндпоинты Admin API

Все пути ниже — относительно хоста и порта приложения (например `http://localhost:8000`).

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/settings` | Все настройки (Telegram + LLM). Секреты маскированы (последние 5 символов). |
| PUT | `/api/settings/telegram` | Сохранить настройки Telegram (accessToken, baseUrl). После сохранения — проверка соединения, при успехе активация и перезапуск бота. |
| DELETE | `/api/settings/telegram` | Удалить сохранённые настройки Telegram (остановка бота). |
| DELETE | `/api/settings/telegram/token` | Отвязать токен (удалить токен, оставить base_url), остановка бота. |
| POST | `/api/settings/telegram/test` | Проверить соединение с Telegram (getMe). |
| POST | `/api/settings/telegram/activate` | Запустить проверку; при успехе пометить настройки как активные и перезапустить бота. |
| PUT | `/api/settings/llm` | Сохранить настройки LLM (провайдер, API key, base URL, модель, system prompt, при необходимости Azure). После сохранения — проверка соединения, при успехе активация. |
| PATCH | `/api/settings/llm` | Обновить только модель, system prompt и (для Azure) endpoint/version. Без проверки соединения. |
| DELETE | `/api/settings/llm` | Удалить сохранённые настройки LLM. |
| DELETE | `/api/settings/llm/token` | Отвязать API key (оставить провайдер, base_url, модель, system prompt). |
| POST | `/api/settings/llm/test` | Проверить соединение с LLM. |
| POST | `/api/settings/llm/activate` | Запустить проверку LLM; при успехе пометить настройки как активные. |
| GET | `/api/settings/llm/providers` | Список провайдеров и моделей (без авторизации). |
| POST | `/api/settings/llm/fetch-models` | Загрузить список моделей с API провайдера (опционально baseUrl, apiKey в body; иначе из сохранённых настроек). |
| GET | `/api/service-admins` | Получить список администраторов сервиса (Telegram-пользователи с привилегиями). |
| POST | `/api/service-admins` | Добавить администратора по Telegram ID (автоматически получает данные профиля из Telegram, если доступно). |
| GET | `/api/service-admins/{telegram_id}` | Получить информацию об администраторе. |
| DELETE | `/api/service-admins/{telegram_id}` | Удалить администратора. |
| POST | `/api/service-admins/{telegram_id}/refresh` | Обновить данные профиля администратора из Telegram. |

Статика админ-панели отдаётся по пути `/admin/` (например `http://localhost:8000/admin/`).

### 4.3 Примеры взаимодействия по API

**Получить настройки (с защитой по ключу):**

```bash
curl -H "X-Admin-Key: YOUR_ADMIN_API_KEY" http://localhost:8000/api/settings
```

**Сохранить настройки Telegram:**

```bash
curl -X PUT http://localhost:8000/api/settings/telegram \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -d '{"accessToken": "123456:ABC-...", "baseUrl": "https://api.telegram.org"}'
```

**Сохранить настройки LLM (OpenAI):**

```bash
curl -X PUT http://localhost:8000/api/settings/llm \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -d '{
    "llmType": "openai",
    "apiKey": "sk-...",
    "baseUrl": "https://api.openai.com/v1",
    "modelType": "gpt-4o-mini",
    "systemPrompt": "Ты помощник."
  }'
```

**Проверить соединение с Telegram:**

```bash
curl -X POST http://localhost:8000/api/settings/telegram/test \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY"
```

**Получить список провайдеров (без ключа):**

```bash
curl http://localhost:8000/api/settings/llm/providers
```

**Добавить администратора сервиса:**

```bash
curl -X POST http://localhost:8000/api/service-admins \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -d '{"telegram_id": 365491351}'
```

**Получить список администраторов:**

```bash
curl -H "X-Admin-Key: YOUR_ADMIN_API_KEY" http://localhost:8000/api/service-admins
```

Таким образом, **по API можно:** управлять настройками Telegram и LLM, проверять соединения, включать/отключать бота (через сохранение/удаление настроек Telegram), управлять списком администраторов сервиса. **Отправлять сообщения пользователям или вызывать LLM напрямую через этот API нельзя** — общение с пользователями идёт только через Telegram-бота по сценарию «пользователь написал → бот отправил в LLM → ответ вернул в чат».

---

## 5. Краткие ответы на вопросы

- **Есть ли API, которое смотрит наружу?**  
  Да: приложение **само** обращается к внешним API — **Telegram Bot API** (long polling и отправка сообщений) и к **API LLM-провайдеров** (OpenAI, Anthropic, Google и др.). Это все исходящие запросы.

- **Можно ли по API взаимодействовать с этим приложением?**  
  Да. При запуске через uvicorn (или Docker) доступен **Admin API** (FastAPI) на порту 8000. Через него можно получать и менять настройки Telegram и LLM, проверять соединения, перезапускать бота, управлять списком администраторов сервиса (привилегированных пользователей Telegram-бота). Для доставки сообщений пользователям или вызова LLM используется только сценарий «пользователь пишет в Telegram → бот → LLM → ответ в чат»; отдельного публичного API для отправки сообщений или чата с LLM в приложении нет.

---

## 6. Переменные окружения (кратко)

- **Бот:** `BOT_TOKEN` (для режима «только бот»).
- **Admin API и БД:** `SETTINGS_ENCRYPTION_KEY` (обязателен для сохранения секретов в БД), опционально `DATABASE_URL`, `ADMIN_API_KEY`.
- **LLM (режим .env):** ключи и модели по провайдерам (см. `.env.example`).

Подробнее — в `README.md` и `docs/LAUNCH_INSTRUCTIONS.md`.
