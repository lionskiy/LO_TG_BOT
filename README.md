# LO_TG_BOT

Telegram bot with an integrated LLM (OpenAI) for chat conversations.

## Requirements

- Python 3.10+
- Bot token from [@BotFather](https://t.me/BotFather)
- [OpenAI](https://platform.openai.com/api-keys) API key

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in the variables:

```bash
cp .env.example .env
```

In `.env`:

- `BOT_TOKEN` — bot token from BotFather
- `OPENAI_API_KEY` — OpenAI key for the LLM

## Running

```bash
python main.py
```

After starting, the bot replies to messages in Telegram using conversation history (last 20 messages) for context.

## Admin API (settings from DB)

To manage Telegram and LLM settings via the web interface, start the server. In `.env` set:

- **`SETTINGS_ENCRYPTION_KEY`** — key for encrypting tokens/keys in the DB. Either set it in `.env`, or **leave it unset in Docker** — on first run the key is created automatically in the volume (`data/.encryption_key`) and persists across restarts. For local runs without Docker: generate the key (with venv active) and add it to `.env`; see [Launch instructions](docs/LAUNCH_INSTRUCTIONS.md) if available.
- **`DATABASE_URL`** — optional; default `sqlite:///./data/settings.db`.
- **`ADMIN_API_KEY`** — optional; if set, all requests to `/api/settings*` require the header `X-Admin-Key: <value>`. Enter this key in the admin panel in the "Admin key" field.

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

On startup, the bot subprocess is started if the DB has active Telegram settings. Admin panel: **http://localhost:8000/admin/**.

**API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | All settings (Telegram + LLM); secrets are masked |
| PUT | `/api/settings/telegram` | Save Telegram settings |
| DELETE | `/api/settings/telegram` | Remove saved Telegram keys (stop the bot) |
| DELETE | `/api/settings/telegram/token` | Unbind token (remove token, keep Base URL) |
| POST | `/api/settings/telegram/test` | Test connection to Telegram |
| POST | `/api/settings/telegram/activate` | Apply Telegram settings (after successful test) |
| PUT | `/api/settings/llm` | Save LLM settings |
| PATCH | `/api/settings/llm` | Update only model and system prompt (no connection test) |
| DELETE | `/api/settings/llm` | Remove saved LLM keys |
| DELETE | `/api/settings/llm/token` | Unbind API key (keep provider, model, Base URL) |
| POST | `/api/settings/llm/test` | Test connection to LLM |
| POST | `/api/settings/llm/activate` | Apply LLM settings |
| GET | `/api/settings/llm/providers` | List of providers and models (no auth) |
| GET | `/api/service-admins` | Get list of service administrators |
| POST | `/api/service-admins` | Add administrator by Telegram ID |
| GET | `/api/service-admins/{telegram_id}` | Get administrator details |
| DELETE | `/api/service-admins/{telegram_id}` | Remove administrator |
| POST | `/api/service-admins/{telegram_id}/refresh` | Refresh profile data from Telegram |

Bot-only mode (no API): `python main.py` — settings from `.env`, as before.

## Commands

- `/start` — greeting and short description

Other text messages are handled by the LLM and get a reply in the same chat.

## Running in Docker (local)

The container runs **API + admin panel** (uvicorn) on port 8000. The bot is started as a subprocess if the DB has active Telegram settings. **One instance per token** — do not run `python main.py` and Docker at the same time.

You need a `.env` file (copy from `.env.example`). The encryption key **does not** need to be set manually: on first container run it is created automatically in volume `bot_data` (file `data/.encryption_key`) and persists across restarts. DB data is also in volume `bot_data`.

```bash
docker compose up --build
```

Admin panel: **http://localhost:8000/admin/**  

To stop: `Ctrl+C`; if needed, `docker compose down`.

Run in background:

```bash
docker compose up -d --build
```

To stop background containers: `docker compose down`.

Run tests in the container:

```bash
docker compose run --rm bot pytest tests/ -v
```
