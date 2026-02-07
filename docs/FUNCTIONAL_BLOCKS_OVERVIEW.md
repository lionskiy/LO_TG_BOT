# Обзор функциональных блоков приложения LO_TG_BOT

> **Назначение:** на основе текущей документации и кода — перечень функциональных блоков приложения и статус их реализации.  
> **Ветка:** docs_creation  
> **Дата:** 2026-02-07

---

## 1. Источники

- **Архитектура и фазы:** [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md), [UPGRADE_TASKS.md](UPGRADE_TASKS.md)
- **Текущая реализация (v1.0):** [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md)
- **Планы фаз:** PLAN_PHASE_0_1 … PLAN_PHASE_6.md
- **Код:** репозиторий (bot/, api/, tools/, plugins/, admin/)
- **Терминология:** плагин = инструмент для оркестратора; у плагина — функции (не инструменты). Подробнее: [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md), раздел Terminology.

---

## 2. Визуальная схема: ядро / инструментарий / плагины

Пункты **1–4** — **ядро** приложения (без них нет ни чата, ни вызова плагинов как инструментов). Всё остальное — **инструментарий** (встроенная инфраструктура) и **надстройки** (плагины; каждый плагин = один инструмент оркестратора, внутри — функции).

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ЯДРО (CORE) — пункты 1–4                                                        │
│  Без ядра приложение не работает как бот с LLM и tool-calling.                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ① Точка входа — Telegram-бот                                                   │
│      • Long polling, приём/отправка сообщений                                     │
│      • Один экземпляр (.bot.pid), управление подпроцессом (bot_runner)            │
│                                                                                  │
│   ② Conversation Manager                                                         │
│      • История диалога по chat_id (20 пар, лимит 500 чатов)                        │
│                                                                                  │
│   ③ LLM Router                                                                   │
│      • Сборка запроса: system_prompt + tools + history + message                  │
│      • Обработка tool_calls, цикл до финального ответа                            │
│                                                                                  │
│   ④ LLM Provider Adapter                                                         │
│      • Многопровайдерность (OpenAI, Anthropic, Google, Groq, …)                    │
│      • Tool-calling для каждого провайдера                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ИНСТРУМЕНТАРИЙ (встроенные блоки) — не плагины                                 │
│  Обеспечивают загрузку, хранение настроек и управление инструментами.            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   • Tool Registry          — каталог инструментов, описания, enabled             │
│   • Plugin Loader          — загрузка из plugins/, plugin.yaml, handlers         │
│   • Plugin Settings Manager — настройки в БД, шифрование, валидация               │
│   • Tool Executor          — вызов handler по имени, таймауты, ошибки           │
│                                                                                  │
│   • Admin API              — /api/settings/*, /api/tools/*, /api/plugins/*,        │
│                             /api/service-admins/*                                │
│   • Админ-панель           — Настройки (TG, LLM), Инструменты, Администраторы    │
│   • Хранилище (SQLite)     — telegram_settings, llm_settings, service_admins,    │
│                             tool_settings                                        │
│   • Шифрование             — Fernet для секретов в БД                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ПЛАГИНЫ (надстройки) — подключаемые модули; каждый плагин = один инструмент      │
│  оркестратора; внутри плагина — функции. plugins/, plugin.yaml, handlers.py.     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Встроенные (built-in):                                                         │
│   ├── plugins/builtin/calculator/     → функции: calculate                       │
│   └── plugins/builtin/datetime_tools/ → функции: get_datetime, get_weekday        │
│                                                                                  │
│   Бизнес-плагины:                                                                │
│   └── plugins/worklog_checker/        → функции: get_worklogs (Jira/Tempo)       │
│       (интеграция с Jira/Tempo пока заглушки)                                    │
│                                                                                  │
│   Планируемые (в доке, в коде нет):                                              │
│   ├── hr_service    — сотрудники, импорт                                          │
│   ├── reminder      — напоминания (с LLM)                                         │
│   └── external calc — пример type: external (HTTP)                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Сводка по слоям

| Слой | Что входит | Роль |
|------|------------|------|
| **Ядро** | ① Точка входа (Telegram-бот) ② Conversation Manager ③ LLM Router ④ LLM Provider Adapter | Обработка сообщений, диалог с LLM, вызов инструментов на уровне провайдера |
| **Инструментарий** | Registry, Loader, Settings Manager, Executor, Admin API, Админ-панель, БД, шифрование | Загрузка плагинов, хранение настроек, управление инструментами и админкой |
| **Плагины** | builtin (calculator, datetime_tools), worklog_checker, будущие (hr_service, reminder, …) | Каждый плагин = один инструмент оркестратора; внутри — функции, бизнес-логика |

---

## 3. Состав приложения: функциональные блоки (детально)

Приложение состоит из следующих **функциональных блоков** (по документации и коду).

### 3.1. Точка входа — Telegram-бот

| Подблок | Описание | Документ |
|--------|----------|----------|
| Long polling | Приём сообщений через getUpdates | ARCHITECTURE_BLUEPRINT, TG_Project_Helper_v1.0 |
| Отправка ответов | sendMessage, ответ пользователю | — |
| Один экземпляр | .bot.pid, защита от двойного запуска | — |
| Управление подпроцессом | Запуск/остановка бота из API (bot_runner) | — |

**Файлы:** `bot/telegram_bot.py`, `bot/single_instance.py`, `run_bot_from_settings.py`, `main.py`, `api/bot_runner.py`

---

### 3.2. Оркестратор (LLM-движок)

| Подблок | Описание | Документ |
|--------|----------|----------|
| Conversation Manager | История по chat_id (до 20 пар user/assistant), лимит 500 чатов | TG_Project_Helper_v1.0 |
| LLM Router | Сборка запроса (system_prompt + tools + history + message), отправка в провайдер | ARCHITECTURE_BLUEPRINT, UPGRADE_TASKS §1 |
| Обработка tool_calls | Разбор ответа LLM, вызов инструментов, цикл до финального текста | PLAN_PHASE_0_1 |
| LLM Provider Adapter | Несколько провайдеров (OpenAI, Anthropic, Google, Groq, OpenRouter, Ollama, Azure, Yandex, Perplexity, xAI, DeepSeek, Custom), tool-calling | TG_Project_Helper_v1.0, PLAN_PHASE_0_1 |

**Файлы:** `bot/telegram_bot.py` (история), `bot/llm.py`, `bot/tool_calling.py`, `api/llm_providers.py`

---

### 3.3. Tool Registry и Plugin Loader

| Подблок | Описание | Документ |
|--------|----------|----------|
| Tool Registry | Список инструментов, описания (EN), параметры (JSON Schema), статус enabled/disabled, сборка tools для LLM | ARCHITECTURE_BLUEPRINT, UPGRADE_TASKS §2 |
| Plugin Loader | Сканирование plugins/, чтение plugin.yaml, загрузка handlers.py, регистрация в Registry, hot-reload | PLAN_PHASE_2 |
| Plugin Settings Manager | Чтение/запись настроек плагинов из БД, шифрование секретов (Fernet), валидация по plugin.yaml | ARCHITECTURE_BLUEPRINT |

**Файлы:** `tools/registry.py`, `tools/loader.py`, `tools/settings_manager.py`, `tools/base.py`, `tools/models.py`

---

### 3.4. Tool Executor

| Подблок | Описание | Документ |
|--------|----------|----------|
| Маршрутизация вызовов | По имени инструмента → handler из Registry | ARCHITECTURE_BLUEPRINT |
| Вызов handler’а плагина | Выполнение функции из handlers.py | — |
| Обработка ошибок и таймауты | Ограничение времени, обработка исключений | UPGRADE_TASKS |

**Файлы:** `tools/executor.py`

---

### 3.5. Плагины (реализованные)

| Плагин | Инструменты | Описание | Документ |
|--------|-------------|----------|----------|
| **builtin/calculator** | calculate | Вычисления по запросу | PLAN_PHASE_2, Block D |
| **builtin/datetime_tools** | get_datetime, get_weekday | Дата/время, день недели | — |
| **worklog_checker** | get_worklogs | Проверка ворклогов (Jira/Tempo) | PLAN_PHASE_6 |

**Файлы:** `plugins/builtin/calculator/`, `plugins/builtin/datetime_tools/`, `plugins/worklog_checker/`

---

### 3.6. Admin API (FastAPI)

| Группа | Эндпоинты | Описание | Документ |
|--------|-----------|----------|----------|
| **Настройки Telegram** | PUT/DELETE /api/settings/telegram, test, activate, token | Сохранение, тест, активация, отвязка токена | TG_Project_Helper_v1.0 §5 |
| **Настройки LLM** | PUT/PATCH/DELETE /api/settings/llm, test, activate, token, providers, fetch-models | CRUD LLM, тест, провайдеры, список моделей | — |
| **Общие настройки** | GET /api/settings | Все настройки (маскирование секретов) | — |
| **Сервисные администраторы** | GET/POST/DELETE /api/service-admins, refresh | CRUD администраторов по Telegram ID | — |
| **Инструменты** | GET/POST /api/tools, GET/PUT /api/tools/{name}, enable, disable, settings, test | Список, включение/выключение, настройки, тест | ARCHITECTURE_BLUEPRINT, PLAN_PHASE_3/4 |
| **Плагины** | GET /api/plugins, POST /api/plugins/reload, POST /api/plugins/{id}/reload | Список плагинов, перезагрузка | — |

**Файлы:** `api/app.py`, `api/tools_router.py`, `api/plugins_router.py`

---

### 3.7. Админ-панель (статический фронт)

| Раздел | Описание | Документ |
|--------|----------|----------|
| **Настройки** | Блоки «Telegram bot» и «LLM» (формы, тест, активация) | TG_Project_Helper_v1.0 |
| **Инструменты** | Список инструментов, вкл/выкл, настройки, тест | PLAN_PHASE_4, Block E |
| **Администраторы** | Список админов, добавление по Telegram ID, удаление | PLAN_PHASE_5, Block F |

**Файлы:** `admin/index.html`, `admin/app.js`, `admin/tools.js`, `admin/admins.js`, `admin/styles.css`

---

### 3.8. Хранилище (SQLite)

| Таблица | Назначение | Документ |
|--------|------------|----------|
| telegram_settings | Токен, base_url, статус подключения, is_active | TG_Project_Helper_v1.0 |
| llm_settings | Провайдер, API key, модель, system prompt, статус, is_active | — |
| service_admins | telegram_id, username, first_name, last_name | — |
| tool_settings | tool_name, plugin_id, enabled, settings_json (шифр.), updated_at | ARCHITECTURE_BLUEPRINT, PLAN_PHASE_3 |

**Файлы:** `api/db.py`, `api/settings_repository.py`, `api/service_admins_repository.py`, `api/tools_repository.py`, `api/encryption.py`

---

### 3.9. Внешние системы

| Система | Использование | Документ |
|--------|----------------|----------|
| Telegram Bot API | getUpdates, sendMessage, getMe | TG_Project_Helper_v1.0 |
| LLM-провайдеры | OpenAI, Anthropic, Google, Groq, OpenRouter, Ollama, Azure, Yandex, Perplexity, xAI, DeepSeek, Custom | — |
| Jira / Tempo | Планируется в worklog_checker (REST API ворклогов) | PLAN_PHASE_6 |

---

## 4. Статус реализации по блокам

| Блок | Статус | Примечание |
|------|--------|------------|
| **Telegram-бот (точка входа)** | Реализован | Long polling, один экземпляр, управление через bot_runner |
| **Conversation Manager** | Реализован | История в telegram_bot.py, лимиты 20 пар / 500 чатов |
| **LLM Router + tool-calling** | Реализован | bot/tool_calling.py, интеграция с bot/llm.py |
| **LLM Provider Adapter (многопровайдерность + tool-calling)** | Реализован | bot/llm.py, api/llm_providers.py |
| **Tool Registry** | Реализован | tools/registry.py |
| **Plugin Loader** | Реализован | tools/loader.py, вызов load_all_plugins в lifespan api/app.py |
| **Plugin Settings Manager** | Реализован | tools/settings_manager.py, sync_settings_with_registry при старте |
| **Tool Executor** | Реализован | tools/executor.py |
| **Builtin-плагины (calculator, datetime_tools)** | Реализованы | plugins/builtin/* |
| **Worklog Checker** | Частично реализован | Плагин и инструмент get_worklogs есть; логика «проверка по Jira/Tempo» заглушена (TODO), реальные вызовы Jira/Tempo API отсутствуют |
| **Admin API: настройки Telegram/LLM** | Реализован | api/app.py |
| **Admin API: service-admins** | Реализован | api/app.py |
| **Admin API: tools** | Реализован | api/tools_router.py |
| **Admin API: plugins (reload)** | Реализован | api/plugins_router.py |
| **Админ-панель: Настройки** | Реализована | admin/index.html, app.js |
| **Админ-панель: Инструменты** | Реализована | admin/tools.js |
| **Админ-панель: Администраторы** | Реализована | admin/admins.js |
| **БД: telegram_settings, llm_settings, service_admins** | Реализовано | api/db.py |
| **БД: tool_settings** | Реализовано | api/db.py, api/tools_repository.py |
| **Шифрование секретов** | Реализовано | api/encryption.py, Fernet |

---

## 5. Сводная таблица: из каких блоков состоит приложение

| № | Функциональный блок | Реализован |
|---|---------------------|------------|
| 1 | Точка входа (Telegram-бот, long polling, один экземпляр, bot_runner) | Да |
| 2 | Оркестратор: Conversation Manager (история, лимиты) | Да |
| 3 | Оркестратор: LLM Router (запрос к LLM, обработка tool_calls, цикл) | Да |
| 4 | Оркестратор: LLM Provider Adapter (многопровайдерность + tool-calling) | Да |
| 5 | Tool Registry (описания, параметры, enabled, формат для LLM) | Да |
| 6 | Plugin Loader (plugins/, plugin.yaml, handlers, hot-reload) | Да |
| 7 | Plugin Settings Manager (БД, шифрование, валидация) | Да |
| 8 | Tool Executor (маршрутизация, вызов handler, ошибки, таймауты) | Да |
| 9 | Плагины: calculator, datetime_tools | Да |
| 10 | Плагин: worklog_checker (каркас + инструмент; Jira/Tempo — заглушки) | Частично |
| 11 | Admin API: настройки Telegram и LLM | Да |
| 12 | Admin API: service-admins | Да |
| 13 | Admin API: tools (list, get, enable/disable, settings, test) | Да |
| 14 | Admin API: plugins (list, reload) | Да |
| 15 | Админ-панель: Настройки (Telegram, LLM) | Да |
| 16 | Админ-панель: Инструменты | Да |
| 17 | Админ-панель: Администраторы | Да |
| 18 | Хранилище: telegram_settings, llm_settings, service_admins, tool_settings | Да |
| 19 | Шифрование секретов в БД | Да |

---

## 6. Что не реализовано / уточнить по документации

- **Worklog Checker:** полная интеграция с Jira/Tempo (поиск пользователя, запрос ворклогов, требуемые часы, дефицит). В коде — заглушки и TODO (см. DOCUMENTATION_AUDIT.md: team resolution, эндпоинты Jira/Tempo).
- **Плагины из планов:** hr_service, reminder, внешний calculator (type: external) — в коде отсутствуют, только в ARCHITECTURE_BLUEPRINT как будущие.
- **Рекомендации аудита документации** (DOCUMENTATION_AUDIT.md): стратегия настроек (per-tool vs per-plugin), порядок старта (plugins → DB → sync), контракты (формат ошибки инструмента, ответ test handler), исправление кодировки/опечаток в PLAN_PHASE_4/5/6 — остаются для последующей проработки.

---

## 7. Версионирование документа

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0 | 2026-02-07 | Первый обзор функциональных блоков по документации и коду |
| 1.1 | 2026-02-07 | Визуальная схема: ядро (1–4), инструментарий, плагины; нумерация разделов 2–7 |
