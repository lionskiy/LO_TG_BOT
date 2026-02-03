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
