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

## Команды

- `/start` — приветствие и краткое описание

Остальные текстовые сообщения обрабатываются LLM и получают ответ в том же чате.

## Запуск в Docker (локально)

Нужен файл `.env` (скопируй из `.env.example` и заполни `BOT_TOKEN` и переменные выбранного LLM). У контейнера есть доступ в сеть (Telegram, API LLM).

```bash
docker compose up --build
```

Остановка: `Ctrl+C` в том же терминале, затем при необходимости `docker compose down`.

Запуск в фоне (контейнеры не остановятся при закрытии терминала):

```bash
docker compose up -d --build
```

Остановка фоновых контейнеров: `docker compose down`.

Запуск тестов в контейнере:

```bash
docker compose run --rm bot pytest tests/ -v
```
