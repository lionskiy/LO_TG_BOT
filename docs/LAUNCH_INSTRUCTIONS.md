# Инструкция по запуску LO_TG_BOT

Пошаговый запуск приложения: только бот, API + админ-панель, Docker.

---

## 1. Подготовка окружения

### 1.1 Клонирование и зависимости

```bash
git clone <repo_url>
cd LO_TG_BOT
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.2 Файл настроек

Скопируй пример конфигурации и отредактируй `.env`:

```bash
cp .env.example .env
```

В `.env` обязательно укажи:

- **`BOT_TOKEN`** — токен бота из [@BotFather](https://t.me/BotFather) (для режима «только бот»).
- Ключ и модель одного из LLM-провайдеров (OpenAI, Anthropic, Google и т.д.) — см. комментарии в `.env.example`.

---

## 2. Режим «только бот» (без админки)

Настройки читаются из `.env`. Запуск:

```bash
python main.py
```

Бот отвечает в Telegram, LLM и токен заданы в `.env`. Админ-панель и API не используются.

---

## 3. Режим API + админ-панель (настройки в БД)

Чтобы управлять настройками Telegram и LLM через веб-интерфейс, нужны дополнительные переменные в `.env`.

### 3.1 Ключ шифрования

Токены и API-ключи в БД хранятся в зашифрованном виде. Есть два варианта:

**Вариант A — автоматически (рекомендуется при запуске в Docker):**  
Не задавай `SETTINGS_ENCRYPTION_KEY` в `.env`. При первом запуске приложение само сгенерирует ключ и сохранит его в файл `data/.encryption_key`. В Docker каталог `data/` лежит в volume, поэтому ключ сохраняется между перезапусками. Ничего вручную настраивать не нужно.

**Вариант B — вручную в `.env` (для локального запуска без Docker):**  
Сгенерируй ключ в окружении проекта (активируй venv или используй `.venv/bin/python`):

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Добавь вывод команды в `.env`: `SETTINGS_ENCRYPTION_KEY=<ключ>`.

Опционально можно задать путь к файлу ключа: `SETTINGS_ENCRYPTION_KEY_FILE=/path/to/key.file` (по умолчанию используется `data/.encryption_key`).

**Важно:** не меняй и не теряй ключ после того, как в БД уже сохранены настройки — иначе расшифровать их будет нельзя.

### 3.2 Остальные переменные (опционально)

- **`DATABASE_URL`** — по умолчанию `sqlite:///./data/settings.db`. Можно не указывать.
- **`ADMIN_API_KEY`** — если задан, доступ к `/api/settings*` только с заголовком `X-Admin-Key: <значение>`. В админ-панели вводится в поле «Admin key».

### 3.3 Запуск API и админки

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

- Админ-панель: **http://localhost:8000/admin/**
- При старте поднимается подпроцесс бота, если в БД есть активные настройки Telegram.

---

## 4. Запуск в Docker

### 4.1 Подготовка

1. Файл `.env` в корне проекта (скопируй из `.env.example`).
2. Ключ шифрования **не обязательно** задавать вручную: при первом запуске контейнера он создаётся автоматически в volume (`data/.encryption_key`) и сохраняется между перезапусками. Если хочешь задать ключ сам — см. раздел **3.1**.
3. При необходимости задай `ADMIN_API_KEY` и `BOT_TOKEN`/ключи LLM в `.env`.

### 4.2 Сборка и запуск

```bash
docker compose up --build
```

Или в фоне:

```bash
docker compose up -d --build
```

- В контейнере работает **API + админ-панель** на порту 8000.
- Админ-панель: **http://localhost:8000/admin/**
- БД (SQLite) хранится в volume `bot_data` и сохраняется между перезапусками.

### 4.3 Остановка

- В foreground-режиме: `Ctrl+C`, затем при необходимости `docker compose down`.
- В фоне: `docker compose down`.

---

## 5. Краткая памятка по ключу шифрования

| Ситуация | Что делать |
|----------|------------|
| **Docker** | Ничего: ключ создаётся автоматически в volume при первом запуске (`data/.encryption_key`) |
| **Локально (uvicorn)** | Либо не задавать — ключ создастся в `data/.encryption_key`; либо сгенерировать и добавить в `.env`: `source .venv/bin/activate`, затем `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, в `.env`: `SETTINGS_ENCRYPTION_KEY=<ключ>` |
| Свой путь к файлу ключа | `SETTINGS_ENCRYPTION_KEY_FILE=/path/to/key.file` |
| Если ключ потерян | Данные в БД расшифровать нельзя; нужно задать новый ключ и заново сохранить настройки в админке |

---

## 6. Ссылки

- [README](../README.md) — общее описание, команды бота, эндпоинты API.
- [Текущая реализация](CURRENT_IMPLEMENTATION.md) — структура проекта и модули.
