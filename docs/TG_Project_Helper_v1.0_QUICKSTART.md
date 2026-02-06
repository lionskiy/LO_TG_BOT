# TG Project Helper v1.0 — Quick start

**Version:** 1.0  
**Date:** February 2026  
**Description:** Short guide for quick setup and frequently asked questions.

> 📖 **Full documentation:** [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md)

---

## Quick start

### 1. Install dependencies

```bash
git clone <repo_url>
cd LO_TG_BOT
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
```

Edit `.env` and set:
- `BOT_TOKEN` — bot token from [@BotFather](https://t.me/BotFather)
- `OPENAI_API_KEY` — OpenAI key (or another provider)

### 3. Run

**Bot-only mode (settings from .env):**
```bash
python main.py
```

**API + admin panel mode (settings in DB):**
```bash
# In .env add SETTINGS_ENCRYPTION_KEY (or leave empty — it will be created automatically)
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Admin panel: **http://localhost:8000/admin/**

**Docker:**
```bash
docker compose up --build
```

Admin panel: **http://localhost:8000/admin/**

---

## FAQ

### How do I check which model the bot is using?

**Via API:**
```bash
curl http://localhost:8000/api/settings | python3 -m json.tool
```

**Via Docker:**
```bash
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

### Why does the bot say it is GPT-3.5 when a different model is set?

This can be due to conversation history. The model may stick to its first reply in context. Try:
1. Clear the conversation history with the bot
2. Ask the question again

Check the actual model via the API (see above) — it should match the settings.

### "Invalid request to model" error when selecting GPT-5

**Causes:**
1. **OpenAI Free tier** — GPT-5 is not available on the free tier
2. **Wrong model name** — use the model list from the "Load model list" button in the admin panel
3. **Limits** — check [Account limits](https://platform.openai.com/account/limits)

**Solution:**
1. Check your tier: [https://platform.openai.com/account/limits](https://platform.openai.com/account/limits)
2. If on Free — add credits for GPT-5 access
3. In the admin panel click "Load model list" and choose a model from the list

### How does the encryption key work?

**In Docker:**  
The key is created automatically on first run in `data/.encryption_key` and persists across restarts. No configuration needed.

**Locally (without Docker):**  
Either leave `SETTINGS_ENCRYPTION_KEY` empty — the key will be created in `data/.encryption_key`. Or generate it manually:

```bash
source .venv/bin/activate
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the output to `.env`: `SETTINGS_ENCRYPTION_KEY=<key>`

**Important:** do not lose the key after saving settings to the DB — otherwise they cannot be decrypted.

### How do I switch model or provider without restarting?

1. Open the admin panel: **http://localhost:8000/admin/**
2. In the "LLM" section select provider and model
3. Click "Save"
4. After a successful connection test, settings are applied automatically

Switching happens on the fly without restarting the application.

### Which providers are supported?

- OpenAI (gpt-4o, gpt-5, o3, o4, etc.)
- Anthropic (Claude)
- Google Gemini
- Groq
- OpenRouter
- Ollama (local models)
- Azure OpenAI
- Yandex GPT
- Perplexity
- xAI (Grok)
- DeepSeek
- Custom (OpenAI-compatible)

### How do I test Telegram/LLM connection?

**In the admin panel:**
- Click the "Retry" button in the Telegram or LLM section
- Status is refreshed automatically every 10 seconds

**Via API:**
```bash
# Test Telegram
curl -X POST http://localhost:8000/api/settings/telegram/test \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY"

# Test LLM
curl -X POST http://localhost:8000/api/settings/llm/test \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY"
```

### How do I add a service administrator?

**Via API:**
```bash
curl -X POST http://localhost:8000/api/service-admins \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -d '{"telegram_id": 123456789}'
```

**Via admin panel:**  
The "Administrators" section in the admin panel is planned for Phase 5 (see [PLAN_PHASE_5.md](PLAN_PHASE_5.md)). For now — only via API or Swagger (http://localhost:8000/docs).

### Where are settings stored?

- **Bot-only mode:** settings in `.env`
- **API + admin panel mode:** settings in SQLite DB (`data/settings.db`)
  - Tokens and API keys are stored encrypted
  - Encryption key in `data/.encryption_key` or in `.env` (`SETTINGS_ENCRYPTION_KEY`)

### How do I view logs?

**Locally:**
```bash
# Logs in console when running uvicorn or python main.py
# Or in a file if LOG_FILE is set in .env
```

**Docker:**
```bash
docker compose logs bot
docker compose logs -f bot  # follow
```

### How do I run tests?

**Locally:**
```bash
pytest tests/ -v
```

**Docker:**
```bash
docker compose run --rm bot pytest tests/ -v
```

---

## Useful links

- **Full documentation:** [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md)
- **OpenAI Account Limits:** [https://platform.openai.com/account/limits](https://platform.openai.com/account/limits)
- **OpenAI Usage:** [https://platform.openai.com/usage](https://platform.openai.com/usage)
- **Telegram BotFather:** [@BotFather](https://t.me/BotFather)
- **Swagger UI (when app is running):** http://localhost:8000/docs

---

## Document versioning

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-02-06 | First version of quick start |
