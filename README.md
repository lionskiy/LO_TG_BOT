# LO_TG_BOT

Telegram-бот с подключённым LLM (OpenAI) для общения в чате.

## Требования

- Python 3.10+
- Токен бота от [@BotFather](https://t.me/BotFather)
- API-ключ [OpenAI](https://platform.openai.com/api-keys)

## Установка

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка

Скопируй `.env.example` в `.env` и заполни переменные:

```bash
cp .env.example .env
```

В `.env`:

- `BOT_TOKEN` — токен бота из BotFather
- `OPENAI_API_KEY` — ключ OpenAI для LLM

## Запуск

```bash
python main.py
```

После запуска бот отвечает на сообщения в Telegram, используя историю диалога (последние 20 реплик) для контекста.

## Admin API (настройки из БД)

Для управления настройками Telegram и LLM через веб-интерфейс запусти сервер. В `.env` задай:

- **`SETTINGS_ENCRYPTION_KEY`** — обязателен для сохранения токенов/ключей в БД (сгенерировать: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- **`DATABASE_URL`** — опционально, по умолчанию `sqlite:///./data/settings.db`.
- **`ADMIN_API_KEY`** — опционально; если задан, все запросы к `/api/settings*` требуют заголовок `X-Admin-Key: <значение>`. В админ-панели введи этот ключ в поле «Admin key».

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

При старте поднимается подпроцесс бота, если в БД есть активные настройки Telegram. Админ-панель: **http://localhost:8000/admin/**.

**Эндпоинты API:**

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/settings` | Все настройки (Telegram + LLM), секреты маскированы |
| PUT | `/api/settings/telegram` | Сохранить настройки Telegram |
| POST | `/api/settings/telegram/test` | Проверить соединение с Telegram |
| POST | `/api/settings/telegram/activate` | Применить настройки Telegram (после успешной проверки) |
| PUT | `/api/settings/llm` | Сохранить настройки LLM |
| POST | `/api/settings/llm/test` | Проверить соединение с LLM |
| POST | `/api/settings/llm/activate` | Применить настройки LLM |
| GET | `/api/settings/llm/providers` | Список провайдеров и моделей (без авторизации) |

Режим «только бот» (без API): `python main.py` — настройки из `.env`, как раньше.

## Команды

- `/start` — приветствие и краткое описание

Остальные текстовые сообщения обрабатываются LLM и получают ответ в том же чате.

## Запуск в Docker (локально)

В контейнере запускается **API + админ-панель** (uvicorn), порт 8000. Бот поднимается подпроцессом, если в БД есть активные настройки Telegram. **Один экземпляр на один токен** — не запускай одновременно `python main.py` и Docker.

Нужен файл `.env` (скопируй из `.env.example`). Для сохранения настроек из админки задай `SETTINGS_ENCRYPTION_KEY` (см. раздел Admin API). Данные БД хранятся в volume `bot_data`.

```bash
docker compose up --build
```

Админ-панель: **http://localhost:8000/admin/**  

Остановка: `Ctrl+C`, при необходимости `docker compose down`.

Запуск в фоне:

```bash
docker compose up -d --build
```

Остановка фоновых контейнеров: `docker compose down`.

Запуск тестов в контейнере:

```bash
docker compose run --rm bot pytest tests/ -v
```
