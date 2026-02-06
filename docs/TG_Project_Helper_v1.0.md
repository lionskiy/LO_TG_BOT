# TG Project Helper v1.0

**Версия:** 1.0  
**Дата:** Февраль 2026  
**Описание:** Полная документация проекта Telegram-бота с поддержкой множества LLM-провайдеров и веб-админ-панелью для управления настройками.

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Архитектура и поток данных](#2-архитектура-и-поток-данных)
3. [Поддерживаемые провайдеры LLM](#3-поддерживаемые-провайдеры-llm)
4. [Установка и запуск](#4-установка-и-запуск)
5. [Admin API](#5-admin-api)
6. [Структура проекта](#6-структура-проекта)
7. [Технические детали](#7-технические-детали)
8. [Рефакторинг и оптимизация](#8-рефакторинг-и-оптимизация)
9. [Решение проблем](#9-решение-проблем)

---

## 1. Обзор проекта

**TG Project Helper** — Telegram-бот с подключённым LLM (большая языковая модель) для общения в чате. Пользователь общается с ботом в Telegram; бот отправляет сообщения выбранному LLM-провайдеру и возвращает ответ в тот же чат.

### Основные возможности

- ✅ Поддержка **12+ LLM-провайдеров**: OpenAI, Anthropic, Google Gemini, Groq, OpenRouter, Ollama, Azure OpenAI, Yandex GPT, Perplexity, xAI, DeepSeek, Custom
- ✅ **Веб-админ-панель** для управления настройками Telegram и LLM через браузер
- ✅ **Hot-swap**: смена бота и LLM без перезапуска приложения
- ✅ **Два режима работы**: только бот (настройки из `.env`) или API + админ-панель (настройки в БД)
- ✅ **Шифрование секретов** в базе данных (Fernet)
- ✅ **История диалога**: последние 20 сообщений для контекста
- ✅ **Управление администраторами** сервиса через Telegram ID

### Режимы работы

| Режим | Как запускается | Откуда настройки |
|-------|------------------|-------------------|
| **Только бот** | `python main.py` | Только `.env` (BOT_TOKEN, ключи LLM) |
| **API + админка** | `uvicorn api.app:app` или Docker | БД (при старте поднимается подпроцесс бота, который читает настройки из БД) |

---

## 2. Архитектура и поток данных

### 2.1 Общая схема

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TG Project Helper                                │
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
            │ Исходящие запросы
            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  Внешний мир                                                               │
│  • Telegram Bot API (api.telegram.org или свой base_url)                   │
│  • LLM-провайдеры: OpenAI, Anthropic, Google, Groq, OpenRouter,           │
│    Ollama, Azure, Yandex GPT, Perplexity, xAI, DeepSeek, custom            │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Как обрабатывается сообщение пользователя

1. Пользователь отправляет боту текстовое сообщение в Telegram
2. Бот (библиотека `python-telegram-bot`) получает обновление через **long polling** — процесс сам периодически опрашивает Telegram API (`getUpdates`)
3. Обработчик собирает контекст: системный промпт (из БД или дефолтный), последние 20 пар user/assistant по этому чату, новое сообщение пользователя
4. Вызывается `get_reply(messages)` в `bot/llm.py`:
   - Сначала проверяется наличие активных настроек LLM в БД (`api.settings_repository.get_llm_settings_decrypted`)
   - Если есть — используются провайдер, модель, API-ключ и системный промпт из БД
   - Если нет — используется конфиг из `.env` (`bot.config.get_active_llm`)
5. Выполняется HTTP-запрос к выбранному LLM-провайдеру
6. Ответ LLM отправляется пользователю в тот же чат через Telegram Bot API; история диалога обновляется

### 2.3 Внешние API (исходящие)

Приложение **само инициирует** запросы к внешним сервисам. Входящих вызовов от внешнего мира к боту (кроме Admin API) нет.

- **Telegram Bot API**: `getUpdates` (long polling), `sendMessage`, `getMe`
- **LLM-провайдеры**: POST-запросы к API провайдеров (Chat Completions, Messages API и т.д.)

---

## 3. Поддерживаемые провайдеры LLM

### 3.1 Список провайдеров

| Провайдер | Base URL по умолчанию | Параметр токенов | Особенности |
|-----------|----------------------|------------------|-------------|
| **OpenAI** | `https://api.openai.com/v1` | `max_tokens` / `max_completion_tokens`* | Новые модели (gpt-5, o3, o4) требуют `max_completion_tokens` |
| **Anthropic** | `https://api.anthropic.com/v1` | `max_tokens` | Нативный API Claude |
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/` | `max_output_tokens` | В `generation_config` |
| **Groq** | `https://api.groq.com/openai/v1` | `max_tokens` / `max_completion_tokens`* | OpenAI-совместимый |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `max_tokens` / `max_completion_tokens`* | Поддерживает оба параметра |
| **Ollama** | `http://localhost:11434/v1` | `max_tokens` | OpenAI-совместимый endpoint |
| **Azure OpenAI** | Зависит от деплоя | `max_tokens` / `max_completion_tokens`* | OpenAI-совместимый |
| **Yandex GPT** | `https://llm.api.cloud.yandex.net` | `maxTokens` | В `completionOptions` |
| **Perplexity** | `https://api.perplexity.ai` | `max_tokens` / `max_completion_tokens`* | OpenAI-совместимый |
| **xAI (Grok)** | `https://api.x.ai/v1` | `max_tokens` / `max_completion_tokens`* | OpenAI-совместимый |
| **DeepSeek** | `https://api.deepseek.com` | `max_tokens` / `max_completion_tokens`* | OpenAI-совместимый |
| **Custom** | Ручной ввод | `max_tokens` / `max_completion_tokens`* | OpenAI-совместимый |

\* Для новых моделей OpenAI (gpt-5, o3, o4) используется `max_completion_tokens`; для старых — `max_tokens`

### 3.2 Параметры токенов по провайдерам

Каждый провайдер использует свой параметр для ограничения длины ответа:

- **OpenAI/Groq/OpenRouter/Ollama/Azure/Perplexity/xAI/DeepSeek/Custom**: 
  - Старые модели: `max_tokens=1024`
  - Новые модели (gpt-5, o3, o4): `max_completion_tokens=1024`
- **Anthropic**: `max_tokens=1024` (нативный API)
- **Google Gemini**: `max_output_tokens=1024` в `generation_config`
- **Yandex GPT**: `maxTokens=1024` в `completionOptions`

---

## 4. Установка и запуск

### 4.1 Подготовка окружения

```bash
git clone <repo_url>
cd LO_TG_BOT
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4.2 Файл настроек

Скопируй пример конфигурации и отредактируй `.env`:

```bash
cp .env.example .env
```

В `.env` обязательно укажи:

- **`BOT_TOKEN`** — токен бота из [@BotFather](https://t.me/BotFather) (для режима «только бот»)
- Ключ и модель одного из LLM-провайдеров (OpenAI, Anthropic, Google и т.д.)

### 4.3 Режим «только бот» (без админки)

Настройки читаются из `.env`. Запуск:

```bash
python main.py
```

Бот отвечает в Telegram, LLM и токен заданы в `.env`. Админ-панель и API не используются.

### 4.4 Режим API + админ-панель (настройки в БД)

#### Ключ шифрования

Токены и API-ключи в БД хранятся в зашифрованном виде. Есть два варианта:

**Вариант A — автоматически (рекомендуется при запуске в Docker):**  
Не задавай `SETTINGS_ENCRYPTION_KEY` в `.env`. При первом запуске приложение само сгенерирует ключ и сохранит его в файл `data/.encryption_key`. В Docker каталог `data/` лежит в volume, поэтому ключ сохраняется между перезапусками.

**Вариант B — вручную в `.env` (для локального запуска без Docker):**  
Сгенерируй ключ:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Добавь вывод команды в `.env`: `SETTINGS_ENCRYPTION_KEY=<ключ>`

**Важно:** не меняй и не теряй ключ после того, как в БД уже сохранены настройки — иначе расшифровать их будет нельзя.

#### Остальные переменные (опционально)

- **`DATABASE_URL`** — по умолчанию `sqlite:///./data/settings.db`. Можно не указывать
- **`ADMIN_API_KEY`** — если задан, доступ к `/api/settings*` только с заголовком `X-Admin-Key: <значение>`. В админ-панели вводится в поле «Admin key»

#### Запуск API и админки

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

- Админ-панель: **http://localhost:8000/admin/**
- При старте поднимается подпроцесс бота, если в БД есть активные настройки Telegram

### 4.5 Запуск в Docker

#### Подготовка

1. Файл `.env` в корне проекта (скопируй из `.env.example`)
2. Ключ шифрования **не обязательно** задавать вручную: при первом запуске контейнера он создаётся автоматически в volume (`data/.encryption_key`) и сохраняется между перезапусками
3. При необходимости задай `ADMIN_API_KEY` и `BOT_TOKEN`/ключи LLM в `.env`

#### Сборка и запуск

```bash
docker compose up --build
```

Или в фоне:

```bash
docker compose up -d --build
```

- В контейнере работает **API + админ-панель** на порту 8000
- Админ-панель: **http://localhost:8000/admin/**
- БД (SQLite) хранится в volume `bot_data` и сохраняется между перезапусками

#### Остановка

- В foreground-режиме: `Ctrl+C`, затем при необходимости `docker compose down`
- В фоне: `docker compose down`

---

## 5. Admin API

### 5.1 Базовые сведения

- **Базовый URL:** например `http://localhost:8000` (порт задаётся при запуске uvicorn)
- **Документация OpenAPI:** при запущенном приложении — `http://localhost:8000/docs` (Swagger UI)
- **Защита:** если в `.env` задан `ADMIN_API_KEY`, все запросы к эндпоинтам ниже должны содержать заголовок:  
  `X-Admin-Key: <значение ADMIN_API_KEY>`.  
  Иначе возвращается 403

### 5.2 Эндпоинты Admin API

Все пути ниже — относительно хоста и порта приложения (например `http://localhost:8000`).

#### Настройки Telegram

| Метод | Путь | Описание |
|-------|------|----------|
| PUT | `/api/settings/telegram` | Сохранить настройки Telegram (accessToken, baseUrl). После сохранения — проверка соединения, при успехе активация и перезапуск бота |
| DELETE | `/api/settings/telegram` | Удалить сохранённые настройки Telegram (остановка бота) |
| DELETE | `/api/settings/telegram/token` | Отвязать токен (удалить токен, оставить base_url), остановка бота |
| POST | `/api/settings/telegram/test` | Проверить соединение с Telegram (getMe) |
| POST | `/api/settings/telegram/activate` | Запустить проверку; при успехе пометить настройки как активные и перезапустить бота |

#### Настройки LLM

| Метод | Путь | Описание |
|-------|------|----------|
| PUT | `/api/settings/llm` | Сохранить настройки LLM (провайдер, API key, base URL, модель, system prompt, при необходимости Azure). После сохранения — проверка соединения, при успехе активация |
| PATCH | `/api/settings/llm` | Обновить только модель, system prompt и (для Azure) endpoint/version. Без проверки соединения |
| DELETE | `/api/settings/llm` | Удалить сохранённые настройки LLM |
| DELETE | `/api/settings/llm/token` | Отвязать API key (оставить провайдер, base_url, модель, system prompt) |
| POST | `/api/settings/llm/test` | Проверить соединение с LLM |
| POST | `/api/settings/llm/activate` | Запустить проверку LLM; при успехе пометить настройки как активные |
| GET | `/api/settings/llm/providers` | Список провайдеров и моделей (без авторизации) |
| POST | `/api/settings/llm/fetch-models` | Загрузить список моделей с API провайдера (опционально baseUrl, apiKey в body; иначе из сохранённых настроек) |

#### Общие настройки

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/settings` | Все настройки (Telegram + LLM). Секреты маскированы (последние 5 символов) |

#### Администраторы сервиса

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/service-admins` | Получить список администраторов сервиса (Telegram-пользователи с привилегиями) |
| POST | `/api/service-admins` | Добавить администратора по Telegram ID (автоматически получает данные профиля из Telegram, если доступно) |
| GET | `/api/service-admins/{telegram_id}` | Получить информацию об администраторе |
| DELETE | `/api/service-admins/{telegram_id}` | Удалить администратора |
| POST | `/api/service-admins/{telegram_id}/refresh` | Обновить данные профиля администратора из Telegram |

Статика админ-панели отдаётся по пути `/admin/` (например `http://localhost:8000/admin/`).

### 5.3 Примеры взаимодействия по API

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

---

## 6. Структура проекта

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
│   ├── settings_repository.py  # CRUD настроек, маскирование для API
│   ├── bot_runner.py           # Запуск/остановка подпроцесса run_bot_from_settings.py
│   ├── telegram_test.py        # Проверка Telegram getMe
│   ├── llm_test.py             # Проверка подключения к LLM
│   ├── llm_providers.py        # Список провайдеров и моделей
│   └── service_admins_repository.py  # CRUD администраторов сервиса
├── admin/
│   ├── index.html              # Админ-панель: блоки Telegram и LLM
│   ├── styles.css
│   └── app.js                  # Загрузка/сохранение, Retry, тосты
├── tests/
│   ├── test_config.py
│   ├── test_llm.py
│   └── test_api_settings.py   # Тесты API настроек
├── docs/
│   └── TG_Project_Helper_v1.0.md  # Эта документация
├── Dockerfile                  # uvicorn api.app, порт 8000
├── docker-compose.yml          # volume bot_data для data/settings.db
├── .env.example
├── requirements.txt
└── README.md
```

---

## 7. Технические детали

### 7.1 Стек и зависимости

- **Язык:** Python 3.11+
- **Основные зависимости:**
  - `python-telegram-bot==21.7` — Telegram Bot API (long polling)
  - `openai==1.55.0`, `httpx>=0.27,<0.28` — OpenAI-совместимые клиенты
  - `anthropic`, `google-generativeai` — Anthropic, Google Gemini
  - `fastapi`, `uvicorn` — Admin API
  - `sqlalchemy` — ORM для БД
  - `cryptography` — шифрование секретов (Fernet)
  - `python-dotenv` — загрузка `.env`
  - `pytest`, `pytest-asyncio` — тесты

### 7.2 База данных

- **По умолчанию:** SQLite (`sqlite:///./data/settings.db`)
- **Модели:**
  - `TelegramSettingsModel` — настройки Telegram (токен, base_url, статус подключения, флаг активности)
  - `LLMSettingsModel` — настройки LLM (провайдер, API key, модель, system prompt, статус подключения, флаг активности)
  - `ServiceAdminModel` — администраторы сервиса (Telegram ID, имя пользователя, имя, фамилия)
- **Шифрование:** API-ключи и токены хранятся в зашифрованном виде (Fernet), ключ шифрования в `data/.encryption_key` или в `.env` (`SETTINGS_ENCRYPTION_KEY`)

### 7.3 История диалога

- История хранится в памяти по `chat_id`
- Ограничение: последние **20 пар** user/assistant на чат
- Ограничение памяти: максимум **500 чатов** в памяти; при превышении удаляется чат с наименьшей историей

### 7.4 Hot-swap (переключение на лету)

- **Telegram бот:** при активации новых настроек Telegram подпроцесс бота перезапускается с новым токеном/Base URL
- **LLM:** настройки читаются из БД при каждом запросе к `get_reply()`, переключение происходит без перезапуска

---

## 8. Рефакторинг и оптимизация

### 8.1 Проблемы, которые были решены

1. **Блокировка event loop** — синхронные вызовы `test_telegram_connection()`, `test_llm_connection()` и работа с Telegram API в эндпоинтах FastAPI выполнялись в основном потоке. При сохранении настроек или добавлении админа сервер мог «зависать» на 10–15+ секунд.

2. **Рост потребления памяти** — история чатов `_chat_history` не ограничивалась по числу чатов и могла расти неограниченно при большом количестве пользователей.

3. **Двойное чтение БД** — в `get_reply()` дважды вызывался `get_llm_settings_decrypted()` (для провайдера и для system_prompt).

4. **Устаревшие API** — использование `session.query()` (deprecated в SQLAlchemy 2.0) и `datetime.utcnow()` (deprecated в Python 3.12+).

### 8.2 Внесённые изменения

#### Производительность и стабильность

- **Эндпоинты не блокируют event loop:**  
  `PUT /api/settings/telegram`, `PUT /api/settings/llm`, `POST .../activate`, а также все эндпоинты service-admins переведены на `async` и выполняют тяжёлую синхронную работу через `asyncio.to_thread()`. Проверка подключения к Telegram/LLM и запросы к Telegram API больше не блокируют обработку других запросов.

- **Ограничение памяти бота:**  
  Введён лимит числа чатов в памяти (`MAX_CHATS_IN_MEMORY = 500`). При превышении лимита удаляется чат с наименьшей историей. Размер истории внутри чата по-прежнему ограничен `MAX_HISTORY_MESSAGES = 20`.

- **Один проход по настройкам LLM:**  
  `_get_llm_from_settings_db()` возвращает кортеж с `system_prompt`; в `get_reply()` больше не вызывается повторно `get_llm_settings_decrypted()`.

#### Качество кода

- **SQLAlchemy 2.0:**  
  В `settings_repository` и `service_admins_repository` запросы переписаны на `select()` / `delete()` и `session.execute()` вместо `session.query()`.

- **Даты в UTC:**  
  Везде заменён устаревший `datetime.utcnow()` на `datetime.now(timezone.utc)`; в `api/db.py` для default/onupdate колонок введена функция `_utc_now()`.

- **Админ-панель (JS):**  
  - Для провайдеров с API списка моделей (OpenAI и др.) при наличии ключа показывается «Загрузка списка моделей...» вместо «Введите API key...» до завершения загрузки
  - Введена общая функция `getConnectionStatusText(status)` для текстов статусов подключения

---

## 9. Решение проблем

### 9.1 Ошибки при выборе модели (OpenAI и др.)

После обновления бот показывает в ответе **текст ошибки от API** — по нему можно понять причину.

#### Частые причины

1. **Тариф OpenAI (Free tier)**  
   В [документации OpenAI](https://platform.openai.com/docs/models/gpt-5) для GPT-5 указано: **Free — Not supported**.  
   То есть на бесплатном тарифе GPT-5 и часть других новых моделей недоступны.

2. **Имя модели**  
   Лучше выбирать модель из списка, загруженного по кнопке **«Загрузить список моделей»** в админ-панели (провайдер OpenAI). Тогда подставляется актуальный `id` из API. Если выбирать только из статичного списка, идентификатор может не совпадать с текущим API.

3. **Лимиты (rate limits)**  
   Даже при платном тарифе есть ограничения RPM/TPM; при превышении приходит ошибка (часто про лимиты).

#### Как проверить доступ и лимиты (OpenAI)

- **Лимиты и тариф:**  
  [https://platform.openai.com/account/limits](https://platform.openai.com/account/limits)  
  Показывает tier и лимиты запросов/токенов. Для GPT-5 нужен минимум Tier 1 (Free — не поддерживается).

- **Использование и биллинг:**  
  [https://platform.openai.com/usage](https://platform.openai.com/usage)  
  Позволяет убедиться, что аккаунт активен и есть доступ к платным моделям.

- **Список моделей по API:**  
  В админ-панели: провайдер OpenAI → сохранить API key → нажать «Загрузить список моделей». В выпадающем списке будут только модели, доступные вашему аккаунту (с учётом тарифа и прав).

#### Что сделать

1. Открыть [Account limits](https://platform.openai.com/account/limits) и проверить tier
2. Если tier Free — для GPT-5 нужно пополнить баланс / перейти на платный доступ
3. В админ-панели бота заново нажать «Загрузить список моделей» и выбрать модель из этого списка
4. Если ошибка повторится — в ответе бота будет приведён текст от API (например, про тариф или имя модели); по нему можно точнее понять причину

### 9.2 Проверка текущей модели

Чтобы проверить, какая модель реально используется ботом:

```bash
# Через API (получить настройки)
curl http://localhost:8000/api/settings | python3 -m json.tool

# Через Docker (проверить настройки в БД)
docker compose exec bot python3 -c "
import sys
sys.path.insert(0, '.')
from api.settings_repository import get_llm_settings_decrypted
settings = get_llm_settings_decrypted()
if settings:
    print(f'Модель: {settings.get(\"model_type\")}')
    print(f'Провайдер: {settings.get(\"llm_type\")}')
"
```

### 9.3 Проблемы с ключом шифрования

| Ситуация | Что делать |
|----------|------------|
| **Docker** | Ничего: ключ создаётся автоматически в volume при первом запуске (`data/.encryption_key`) |
| **Локально (uvicorn)** | Либо не задавать — ключ создастся в `data/.encryption_key`; либо сгенерировать и добавить в `.env`: `source .venv/bin/activate`, затем `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, в `.env`: `SETTINGS_ENCRYPTION_KEY=<ключ>` |
| Свой путь к файлу ключа | `SETTINGS_ENCRYPTION_KEY_FILE=/path/to/key.file` |
| Если ключ потерян | Данные в БД расшифровать нельзя; нужно задать новый ключ и заново сохранить настройки в админке |

---

## Планируемое развитие

Документы по планам развития (tool-calling, плагины, админка инструментов/администраторов, Worklog Checker) находятся в той же папке `docs/`:

- [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) — целевая архитектура
- [UPGRADE_TASKS.md](UPGRADE_TASKS.md) — декомпозиция задач по фазам
- [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) … [PLAN_PHASE_6.md](PLAN_PHASE_6.md) — детальные планы фаз

Текущая реализация (v1.0) служит базой для этих планов.

---

## Версионирование документа

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0 | 2026-02-06 | Первая версия объединённой документации |
