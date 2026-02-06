# TG Project Helper v1.0

**Version:** 1.0  
**Date:** February 2026  
**Description:** Full documentation of the Telegram bot project with support for multiple LLM providers and a web admin panel for managing settings.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Architecture and data flow](#2-architecture-and-data-flow)
3. [Supported LLM providers](#3-supported-llm-providers)
4. [Installation and running](#4-installation-and-running)
5. [Admin API](#5-admin-api)
6. [Project structure](#6-project-structure)
7. [Technical details](#7-technical-details)
8. [Refactoring and optimization](#8-refactoring-and-optimization)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Project overview

**TG Project Helper** is a Telegram bot with an integrated LLM (large language model) for chat. The user talks to the bot in Telegram; the bot sends messages to the selected LLM provider and returns the reply in the same chat.

### Main features

- ✅ Support for **12+ LLM providers**: OpenAI, Anthropic, Google Gemini, Groq, OpenRouter, Ollama, Azure OpenAI, Yandex GPT, Perplexity, xAI, DeepSeek, Custom
- ✅ **Web admin panel** for managing Telegram and LLM settings in the browser
- ✅ **Hot-swap**: change bot and LLM without restarting the application
- ✅ **Two operation modes**: bot only (settings from `.env`) or API + admin panel (settings in DB)
- ✅ **Secret encryption** in the database (Fernet)
- ✅ **Conversation history**: last 20 messages for context
- ✅ **Service administrator management** by Telegram ID

### Operation modes

| Mode | How to run | Where settings come from |
|------|------------|---------------------------|
| **Bot only** | `python main.py` | `.env` only (BOT_TOKEN, LLM keys) |
| **API + admin** | `uvicorn api.app:app` or Docker | DB (on startup the bot subprocess is started and reads settings from DB) |

---

## 2. Architecture and data flow

### 2.1 High-level diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TG Project Helper                                │
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────┐     ┌────────────────┐ │
│  │  Telegram Bot     │     │  Admin FastAPI    │     │  SQLite (DB)    │ │
│  │  (long polling)   │     │  :8000            │     │  settings.db    │ │
│  │  run_bot_*.py     │     │  /api/settings*   │     │  (secrets       │ │
│  │  or main.py       │     │  /admin/          │     │   encrypted)    │ │
│  └────────┬─────────┘     └────────┬──────────┘     └────────┬────────┘ │
│           │                        │                          │          │
│           │                        └──────────────────────────┘          │
│           │                                     read/write settings       │
│           │                                                                 │
│           ▼                                                                 │
│  ┌──────────────────┐                                                      │
│  │  bot/llm.py      │  get_reply(messages) → call active LLM               │
│  │  (priority: DB   │                                                      │
│  │   then .env)     │                                                      │
│  └────────┬─────────┘                                                      │
└───────────┼───────────────────────────────────────────────────────────────┘
            │
            │ Outgoing requests
            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  External world                                                            │
│  • Telegram Bot API (api.telegram.org or custom base_url)                   │
│  • LLM providers: OpenAI, Anthropic, Google, Groq, OpenRouter,             │
│    Ollama, Azure, Yandex GPT, Perplexity, xAI, DeepSeek, custom            │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2.2 How a user message is processed

1. The user sends a text message to the bot in Telegram
2. The bot (library `python-telegram-bot`) receives updates via **long polling** — the process periodically polls the Telegram API (`getUpdates`)
3. The handler builds context: system prompt (from DB or default), last 20 user/assistant pairs for this chat, and the new user message
4. `get_reply(messages)` is called in `bot/llm.py`:
   - First it checks for active LLM settings in the DB (`api.settings_repository.get_llm_settings_decrypted`)
   - If present — provider, model, API key, and system prompt from DB are used
   - If not — config from `.env` is used (`bot.config.get_active_llm`)
5. An HTTP request is sent to the selected LLM provider
6. The LLM reply is sent to the user in the same chat via the Telegram Bot API; conversation history is updated

### 2.3 External APIs (outgoing)

The application **initiates** requests to external services. There are no incoming calls from the outside to the bot (except the Admin API).

- **Telegram Bot API**: `getUpdates` (long polling), `sendMessage`, `getMe`
- **LLM providers**: POST requests to provider APIs (Chat Completions, Messages API, etc.)

---

## 3. Supported LLM providers

### 3.1 Provider list

| Provider | Default Base URL | Token parameter | Notes |
|----------|------------------|-----------------|-------|
| **OpenAI** | `https://api.openai.com/v1` | `max_tokens` / `max_completion_tokens`* | New models (gpt-5, o3, o4) require `max_completion_tokens` |
| **Anthropic** | `https://api.anthropic.com/v1` | `max_tokens` | Native Claude API |
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/` | `max_output_tokens` | In `generation_config` |
| **Groq** | `https://api.groq.com/openai/v1` | `max_tokens` / `max_completion_tokens`* | OpenAI-compatible |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `max_tokens` / `max_completion_tokens`* | Supports both parameters |
| **Ollama** | `http://localhost:11434/v1` | `max_tokens` | OpenAI-compatible endpoint |
| **Azure OpenAI** | Depends on deployment | `max_tokens` / `max_completion_tokens`* | OpenAI-compatible |
| **Yandex GPT** | `https://llm.api.cloud.yandex.net` | `maxTokens` | In `completionOptions` |
| **Perplexity** | `https://api.perplexity.ai` | `max_tokens` / `max_completion_tokens`* | OpenAI-compatible |
| **xAI (Grok)** | `https://api.x.ai/v1` | `max_tokens` / `max_completion_tokens`* | OpenAI-compatible |
| **DeepSeek** | `https://api.deepseek.com` | `max_tokens` / `max_completion_tokens`* | OpenAI-compatible |
| **Custom** | Manual input | `max_tokens` / `max_completion_tokens`* | OpenAI-compatible |

\* For new OpenAI models (gpt-5, o3, o4) use `max_completion_tokens`; for older models use `max_tokens`

### 3.2 Token parameters by provider

Each provider uses its own parameter to limit response length:

- **OpenAI/Groq/OpenRouter/Ollama/Azure/Perplexity/xAI/DeepSeek/Custom**: 
  - Older models: `max_tokens=1024`
  - New models (gpt-5, o3, o4): `max_completion_tokens=1024`
- **Anthropic**: `max_tokens=1024` (native API)
- **Google Gemini**: `max_output_tokens=1024` in `generation_config`
- **Yandex GPT**: `maxTokens=1024` in `completionOptions`

---

## 4. Installation and running

### 4.1 Environment setup

```bash
git clone <repo_url>
cd LO_TG_BOT
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4.2 Configuration file

Copy the example config and edit `.env`:

```bash
cp .env.example .env
```

In `.env` you must set:

- **`BOT_TOKEN`** — bot token from [@BotFather](https://t.me/BotFather) (for bot-only mode)
- Key and model for one of the LLM providers (OpenAI, Anthropic, Google, etc.)

### 4.3 Bot-only mode (no admin panel)

Settings are read from `.env`. Run:

```bash
python main.py
```

The bot replies in Telegram; LLM and token are set in `.env`. Admin panel and API are not used.

### 4.4 API + admin panel mode (settings in DB)

#### Encryption key

Tokens and API keys in the DB are stored encrypted. Two options:

**Option A — automatic (recommended when running in Docker):**  
Do not set `SETTINGS_ENCRYPTION_KEY` in `.env`. On first run the application generates the key and saves it to `data/.encryption_key`. In Docker the `data/` directory is in a volume, so the key persists across restarts.

**Option B — manually in `.env` (for local run without Docker):**  
Generate the key:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the command output to `.env`: `SETTINGS_ENCRYPTION_KEY=<key>`

**Important:** do not change or lose the key after settings are saved to the DB — otherwise they cannot be decrypted.

#### Other variables (optional)

- **`DATABASE_URL`** — default `sqlite:///./data/settings.db`. Can be omitted
- **`ADMIN_API_KEY`** — if set, access to `/api/settings*` requires the header `X-Admin-Key: <value>`. Enter it in the admin panel in the "Admin key" field

#### Running API and admin panel

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

- Admin panel: **http://localhost:8000/admin/**
- On startup the bot subprocess is started if the DB has active Telegram settings

### 4.5 Running in Docker

#### Preparation

1. `.env` file in the project root (copy from `.env.example`)
2. Encryption key **does not** need to be set manually: on first container run it is created automatically in the volume (`data/.encryption_key`) and persists across restarts
3. If needed, set `ADMIN_API_KEY` and `BOT_TOKEN`/LLM keys in `.env`

#### Build and run

```bash
docker compose up --build
```

Or in background:

```bash
docker compose up -d --build
```

- The container runs **API + admin panel** on port 8000
- Admin panel: **http://localhost:8000/admin/**
- DB (SQLite) is stored in volume `bot_data` and persists across restarts

#### Stopping

- Foreground: `Ctrl+C`, then if needed `docker compose down`
- Background: `docker compose down`

---

## 5. Admin API

### 5.1 Basics

- **Base URL:** e.g. `http://localhost:8000` (port is set when starting uvicorn)
- **OpenAPI docs:** when the app is running — `http://localhost:8000/docs` (Swagger UI)
- **Protection:** if `ADMIN_API_KEY` is set in `.env`, all requests to the endpoints below must include the header:  
  `X-Admin-Key: <ADMIN_API_KEY value>`.  
  Otherwise 403 is returned

### 5.2 Admin API endpoints

All paths below are relative to the app host and port (e.g. `http://localhost:8000`).

#### Telegram settings

| Method | Path | Description |
|--------|------|-------------|
| PUT | `/api/settings/telegram` | Save Telegram settings (accessToken, baseUrl). After save — connection test; on success, activation and bot restart |
| DELETE | `/api/settings/telegram` | Remove saved Telegram settings (stop the bot) |
| DELETE | `/api/settings/telegram/token` | Unbind token (remove token, keep base_url); stop the bot |
| POST | `/api/settings/telegram/test` | Test connection to Telegram (getMe) |
| POST | `/api/settings/telegram/activate` | Run test; on success mark settings as active and restart the bot |

#### LLM settings

| Method | Path | Description |
|--------|------|-------------|
| PUT | `/api/settings/llm` | Save LLM settings (provider, API key, base URL, model, system prompt, Azure if needed). After save — connection test; on success, activation |
| PATCH | `/api/settings/llm` | Update only model, system prompt, and (for Azure) endpoint/version. No connection test |
| DELETE | `/api/settings/llm` | Remove saved LLM settings |
| DELETE | `/api/settings/llm/token` | Unbind API key (keep provider, base_url, model, system prompt) |
| POST | `/api/settings/llm/test` | Test connection to LLM |
| POST | `/api/settings/llm/activate` | Run LLM test; on success mark settings as active |
| GET | `/api/settings/llm/providers` | List of providers and models (no auth) |
| POST | `/api/settings/llm/fetch-models` | Fetch model list from provider API (optional baseUrl, apiKey in body; otherwise from saved settings) |

#### General settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | All settings (Telegram + LLM). Secrets masked (last 5 characters) |

#### Service administrators

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/service-admins` | Get list of service administrators (Telegram users with privileges) |
| POST | `/api/service-admins` | Add administrator by Telegram ID (profile data fetched from Telegram if available) |
| GET | `/api/service-admins/{telegram_id}` | Get administrator details |
| DELETE | `/api/service-admins/{telegram_id}` | Remove administrator |
| POST | `/api/service-admins/{telegram_id}/refresh` | Refresh administrator profile data from Telegram |

Admin panel static files are served at `/admin/` (e.g. `http://localhost:8000/admin/`).

### 5.3 API usage examples

**Get settings (with key protection):**

```bash
curl -H "X-Admin-Key: YOUR_ADMIN_API_KEY" http://localhost:8000/api/settings
```

**Save Telegram settings:**

```bash
curl -X PUT http://localhost:8000/api/settings/telegram \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -d '{"accessToken": "123456:ABC-...", "baseUrl": "https://api.telegram.org"}'
```

**Save LLM settings (OpenAI):**

```bash
curl -X PUT http://localhost:8000/api/settings/llm \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -d '{
    "llmType": "openai",
    "apiKey": "sk-...",
    "baseUrl": "https://api.openai.com/v1",
    "modelType": "gpt-4o-mini",
    "systemPrompt": "You are a helpful assistant."
  }'
```

---

## 6. Project structure

```
LO_TG_BOT/
├── main.py                     # Entry point: bot only, settings from .env
├── run_bot_from_settings.py    # Run bot from DB settings (API subprocess)
├── bot/
│   ├── config.py               # .env, active LLM (fallback when no DB)
│   ├── llm.py                  # get_reply(): priority — DB, then .env
│   ├── single_instance.py      # .bot.pid, single instance
│   └── telegram_bot.py         # Handlers, run_polling(), run_polling_with_token()
├── api/
│   ├── app.py                  # FastAPI: /api/settings*, serve admin/
│   ├── db.py                   # SQLAlchemy, TelegramSettingsModel, LLMSettingsModel
│   ├── encryption.py           # Fernet: encrypt tokens/keys for DB
│   ├── settings_repository.py  # CRUD for settings, masking for API
│   ├── bot_runner.py           # Start/stop subprocess run_bot_from_settings.py
│   ├── telegram_test.py        # Telegram getMe test
│   ├── llm_test.py             # LLM connection test
│   ├── llm_providers.py        # List of providers and models
│   └── service_admins_repository.py  # CRUD for service administrators
├── admin/
│   ├── index.html              # Admin panel: Telegram and LLM sections
│   ├── styles.css
│   └── app.js                  # Load/save, Retry, toasts
├── tests/
│   ├── test_config.py
│   ├── test_llm.py
│   └── test_api_settings.py   # API settings tests
├── docs/
│   └── TG_Project_Helper_v1.0.md  # This documentation
├── Dockerfile                  # uvicorn api.app, port 8000
├── docker-compose.yml          # volume bot_data for data/settings.db
├── .env.example
├── requirements.txt
└── README.md
```

---

## 7. Technical details

### 7.1 Stack and dependencies

- **Language:** Python 3.11+
- **Main dependencies:**
  - `python-telegram-bot==21.7` — Telegram Bot API (long polling)
  - `openai==1.55.0`, `httpx>=0.27,<0.28` — OpenAI-compatible clients
  - `anthropic`, `google-generativeai` — Anthropic, Google Gemini
  - `fastapi`, `uvicorn` — Admin API
  - `sqlalchemy` — ORM for DB
  - `cryptography` — secret encryption (Fernet)
  - `python-dotenv` — load `.env`
  - `pytest`, `pytest-asyncio` — tests

### 7.2 Database

- **Default:** SQLite (`sqlite:///./data/settings.db`)
- **Models:**
  - `TelegramSettingsModel` — Telegram settings (token, base_url, connection status, active flag)
  - `LLMSettingsModel` — LLM settings (provider, API key, model, system prompt, connection status, active flag)
  - `ServiceAdminModel` — service administrators (Telegram ID, username, first name, last name)
- **Encryption:** API keys and tokens are stored encrypted (Fernet); encryption key in `data/.encryption_key` or in `.env` (`SETTINGS_ENCRYPTION_KEY`)

### 7.3 Conversation history

- History is kept in memory by `chat_id`
- Limit: last **20 pairs** of user/assistant per chat
- Memory limit: at most **500 chats** in memory; when exceeded, the chat with the smallest history is removed

### 7.4 Hot-swap (switch on the fly)

- **Telegram bot:** when new Telegram settings are activated, the bot subprocess is restarted with the new token/Base URL
- **LLM:** settings are read from the DB on every `get_reply()` call; switching happens without restart

---

## 8. Refactoring and optimization

### 8.1 Issues that were addressed

1. **Event loop blocking** — synchronous calls to `test_telegram_connection()`, `test_llm_connection()` and Telegram API usage in FastAPI endpoints ran in the main thread. When saving settings or adding an admin, the server could "hang" for 10–15+ seconds.

2. **Memory growth** — chat history `_chat_history` was not limited by number of chats and could grow without bound with many users.

3. **Double DB read** — in `get_reply()`, `get_llm_settings_decrypted()` was called twice (for provider and for system_prompt).

4. **Deprecated APIs** — use of `session.query()` (deprecated in SQLAlchemy 2.0) and `datetime.utcnow()` (deprecated in Python 3.12+).

### 8.2 Changes made

#### Performance and stability

- **Endpoints do not block the event loop:**  
  `PUT /api/settings/telegram`, `PUT /api/settings/llm`, `POST .../activate`, and all service-admins endpoints are now `async` and run heavy synchronous work via `asyncio.to_thread()`. Telegram/LLM connection tests and Telegram API requests no longer block other requests.

- **Bot memory limit:**  
  A limit on number of chats in memory (`MAX_CHATS_IN_MEMORY = 500`) was added. When exceeded, the chat with the smallest history is removed. Per-chat history size remains limited to `MAX_HISTORY_MESSAGES = 20`.

- **Single pass for LLM settings:**  
  `_get_llm_from_settings_db()` returns a tuple including `system_prompt`; `get_reply()` no longer calls `get_llm_settings_decrypted()` again.

#### Code quality

- **SQLAlchemy 2.0:**  
  In `settings_repository` and `service_admins_repository`, queries were rewritten to use `select()` / `delete()` and `session.execute()` instead of `session.query()`.

- **UTC dates:**  
  Deprecated `datetime.utcnow()` was replaced with `datetime.now(timezone.utc)` everywhere; in `api/db.py` a `_utc_now()` function was added for default/onupdate columns.

- **Admin panel (JS):**  
  - For providers with a model list API (OpenAI, etc.), when a key is present, "Loading model list..." is shown instead of "Enter API key..." until loading finishes
  - A shared function `getConnectionStatusText(status)` was added for connection status text

---

## 9. Troubleshooting

### 9.1 Model selection errors (OpenAI and others)

After the update, the bot shows **the API error text** in the reply — you can use it to identify the cause.

#### Common causes

1. **OpenAI tier (Free tier)**  
   In [OpenAI documentation](https://platform.openai.com/docs/models/gpt-5) for GPT-5: **Free — Not supported**.  
   So on the free tier, GPT-5 and some other new models are not available.

2. **Model name**  
   Prefer choosing the model from the list loaded via **"Load model list"** in the admin panel (OpenAI provider). That uses the current `id` from the API. If you only use the static list, the identifier may not match the current API.

3. **Rate limits**  
   Even on a paid tier there are RPM/TPM limits; exceeding them returns an error (often about limits).

#### How to check access and limits (OpenAI)

- **Limits and tier:**  
  [https://platform.openai.com/account/limits](https://platform.openai.com/account/limits)  
  Shows tier and request/token limits. For GPT-5 you need at least Tier 1 (Free is not supported).

- **Usage and billing:**  
  [https://platform.openai.com/usage](https://platform.openai.com/usage)  
  Lets you confirm the account is active and has access to paid models.

- **Model list via API:**  
  In the admin panel: OpenAI provider → save API key → click "Load model list". The dropdown will only show models available to your account (according to tier and permissions).

#### What to do

1. Open [Account limits](https://platform.openai.com/account/limits) and check your tier
2. If tier is Free — for GPT-5 you need to add credits or switch to paid access
3. In the bot admin panel click "Load model list" again and choose a model from that list
4. If the error persists — the bot reply will include the API text (e.g. about tier or model name); use it to pinpoint the cause

### 9.2 Checking the current model

To see which model the bot is actually using:

```bash
# Via API (get settings)
curl http://localhost:8000/api/settings | python3 -m json.tool

# Via Docker (check settings in DB)
docker compose exec bot python3 -c "
import sys
sys.path.insert(0, '.')
from api.settings_repository import get_llm_settings_decrypted
settings = get_llm_settings_decrypted()
if settings:
    print(f'Model: {settings.get(\"model_type\")}')
    print(f'Provider: {settings.get(\"llm_type\")}')
"
```

### 9.3 Encryption key issues

| Situation | What to do |
|-----------|------------|
| **Docker** | Nothing: key is created automatically in the volume on first run (`data/.encryption_key`) |
| **Local (uvicorn)** | Either leave it unset — key will be created in `data/.encryption_key`; or generate and add to `.env`: `source .venv/bin/activate`, then `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, in `.env`: `SETTINGS_ENCRYPTION_KEY=<key>` |
| Custom key file path | `SETTINGS_ENCRYPTION_KEY_FILE=/path/to/key.file` |
| Key lost | Data in DB cannot be decrypted; set a new key and save settings again in the admin panel |

---

## Planned evolution

Documents for planned evolution (tool-calling, plugins, tools/admin panel, Worklog Checker) are in the same `docs/` folder:

- [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) — target architecture
- [UPGRADE_TASKS.md](UPGRADE_TASKS.md) — task breakdown by phase
- [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) … [PLAN_PHASE_6.md](PLAN_PHASE_6.md) — detailed phase plans

The current implementation (v1.0) is the base for these plans.

---

## Document versioning

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-02-06 | First version of consolidated documentation |
