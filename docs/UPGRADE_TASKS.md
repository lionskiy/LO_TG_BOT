# UPGRADE TASKS — LO_TG_BOT

> **Task breakdown for project evolution**  
> Detailed to 3–4 levels for planning and tracking

**Version:** 1.1  
**Date:** 2026-02-06

---

## Related documents

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target system architecture | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Task breakdown (this document) | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Detailed plan for Phase 0–1 | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Detailed plan for Phase 2 (Plugin System) | ✅ Current (in progress) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Detailed plan for Phase 3 (Storage + API) | ✅ Current (in progress) |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Detailed plan for Phase 4 (Admin Tools) | ✅ Current (in progress) |
| [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Detailed plan for Phase 5 (Admin Administrators) | ✅ Current (in progress) |
| [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Detailed plan for Phase 6 (Worklog Checker) | ✅ Current (in progress) |

### Current state (v1.0) — implemented

| Document | Description |
|----------|-------------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Full specification of current implementation |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

---

## How to use this document

1. **When planning a sprint** — pick a block/subblock from the required phase
2. **When developing** — check against the done criteria
3. **When doing code review** — verify all sub-items are done
4. **When testing** — use the done criteria as a checklist
5. **Detailed phase plan** — see the corresponding PLAN_PHASE_X.md
6. **Architecture questions** — see [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md)

---

## Functional blocks (full breakdown)

---

## 1. LLM ENGINE (Orchestrator) — EXTENSION

```
1. LLM ENGINE
│
├── 1.1 LLM Router [NEW]
│   │
│   ├── 1.1.1 Request building
│   │   ├── Build system_prompt (English)
│   │   ├── Get tools from Registry
│   │   ├── Add conversation history
│   │   └── Add user message
│   │
│   ├── 1.1.2 LLM response handling
│   │   ├── Check for tool_calls
│   │   ├── Parse function name and arguments
│   │   ├── Call Tool Executor
│   │   └── Build tool_result message
│   │
│   ├── 1.1.3 Tool-calling loop
│   │   ├── Follow-up request to LLM with result
│   │   ├── Support multiple tool calls
│   │   ├── Depth limit (max iterations)
│   │   └── Get final text reply
│   │
│   ├── 1.1.4 Error handling
│   │   ├── Tool not found
│   │   ├── Tool execution error
│   │   ├── LLM timeout/error
│   │   └── Fallback to normal reply
│   │
│   ├── Files:
│   │   └── bot/tool_calling.py [NEW]
│   │
│   ├── Dependencies: Tool Registry, Tool Executor
│   │
│   └── Done when:
│       └── LLM selects and calls tools, returns reply
│
├── 1.2 LLM Provider Adapter [EXTENSION]
│   │
│   ├── 1.2.1 OpenAI / OpenAI-compatible
│   │   ├── Add tools parameter to request
│   │   ├── Add tool_choice parameter
│   │   ├── Handle response.tool_calls
│   │   └── Build tool result message
│   │
│   ├── 1.2.2 Anthropic (Claude)
│   │   ├── Convert tools to Anthropic format
│   │   ├── Handle tool_use blocks
│   │   └── Build tool_result content
│   │
│   ├── 1.2.3 Google (Gemini)
│   │   ├── Convert tools to Gemini format
│   │   ├── Handle function_call response
│   │   └── Build function_response
│   │
│   ├── 1.2.4 Universal interface
│   │   ├── ToolCall abstraction (name, arguments, id)
│   │   ├── ToolResult abstraction (id, content)
│   │   └── Converters per provider
│   │
│   ├── Files:
│   │   └── bot/llm.py [EXTENSION]
│   │
│   ├── Dependencies: None
│   │
│   └── Done when:
│       └── Tool-calling works for OpenAI, Anthropic, Google
```

---

## 2. PLUGIN SYSTEM — NEW

```
2. PLUGIN SYSTEM
│
├── 2.1 Tool Registry [NEW]
│   │
│   ├── 2.1.1 Структуры данных
│   │   ├── ToolDefinition (name, description, parameters, handler, timeout)
│   │   ├── PluginManifest (id, name, version, tools, settings)
│   │   └── ToolStatus (enabled, needs_config, error)
│   │
│   ├── 2.1.2 Хранение в памяти
│   │   ├── Dict[tool_name, ToolDefinition]
│   │   ├── Dict[plugin_id, PluginManifest]
│   │   └── Синхронизация с БД (статусы, настройки)
│   │
│   ├── 2.1.3 API для LLM Router
│   │   ├── get_enabled_tools() → List[ToolDefinition]
│   │   ├── get_tools_for_llm() → List[dict] (OpenAI format)
│   │   └── get_tool(name) → ToolDefinition | None
│   │
│   ├── 2.1.4 API для управления
│   │   ├── enable_tool(name)
│   │   ├── disable_tool(name)
│   │   ├── get_tool_status(name) → ToolStatus
│   │   └── list_all_tools() → List[ToolDefinition]
│   │
│   ├── Files:
│   │   ├── tools/__init__.py
│   │   ├── tools/registry.py [NEW]
│   │   └── tools/models.py [NEW]
│   │
│   ├── Dependencies: Plugin Loader
│   │
│   └── Done when:
│       └── Registry хранит tools и формирует список для LLM
│
├── 2.2 Plugin Loader [NEW]
│   │
│   ├── 2.2.1 Сканирование
│   │   ├── Обход папки plugins/
│   │   ├── Поиск plugin.yaml в каждой подпапке
│   │   └── Фильтрация (игнорировать __pycache__, .git и т.д.)
│   │
│   ├── 2.2.2 Парсинг манифеста
│   │   ├── Чтение plugin.yaml (PyYAML)
│   │   ├── Валидация схемы (Pydantic)
│   │   ├── Проверка обязательных полей
│   │   └── Обработка ошибок парсинга
│   │
│   ├── 2.2.3 Загрузка кода
│   │   ├── importlib.util для handlers.py
│   │   ├── Получение функций-handlers
│   │   ├── Валидация сигнатур функций
│   │   └── Обработка ошибок импорта
│   │
│   ├── 2.2.4 Регистрация
│   │   ├── Создание ToolDefinition для каждого tool
│   │   ├── Регистрация в Registry
│   │   └── Логирование загруженных плагинов
│   │
│   ├── 2.2.5 Hot-reload
│   │   ├── reload_plugin(plugin_id)
│   │   ├── reload_all_plugins()
│   │   ├── Удаление старых tools из Registry
│   │   └── Загрузка обновлённых
│   │
│   ├── Files:
│   │   └── tools/loader.py [NEW]
│   │
│   ├── Dependencies: None
│   │
│   └── Done when:
│       └── Плагины загружаются из папки при старте и по команде
│
├── 2.3 Tool Executor [NEW]
│   │
│   ├── 2.3.1 Маршрутизация
│   │   ├── Получение handler из Registry по имени
│   │   ├── Проверка что tool enabled
│   │   └── Проверка что настройки заполнены
│   │
│   ├── 2.3.2 Выполнение
│   │   ├── Парсинг arguments (JSON → dict)
│   │   ├── Вызов async handler(**kwargs)
│   │   ├── Сериализация результата (dict/str → str)
│   │   └── Обработка возвращаемого значения
│   │
│   ├── 2.3.3 Таймауты
│   │   ├── asyncio.wait_for с timeout из ToolDefinition
│   │   ├── Дефолтный timeout (30 сек)
│   │   └── Обработка asyncio.TimeoutError
│   │
│   ├── 2.3.4 Обработка ошибок
│   │   ├── Tool not found → ToolNotFoundError
│   │   ├── Tool disabled → ToolDisabledError
│   │   ├── Execution error → ToolExecutionError
│   │   └── Формирование error message для LLM
│   │
│   ├── 2.3.5 Логирование
│   │   ├── Лог: tool_name, params, duration, result/error
│   │   ├── Опционально: запись в tool_call_log (БД)
│   │   └── Метрики (счётчики вызовов)
│   │
│   ├── Files:
│   │   └── tools/executor.py [NEW]
│   │
│   ├── Dependencies: Tool Registry
│   │
│   └── Done when:
│       └── Executor вызывает handlers и возвращает результат
│
├── 2.4 Plugin Settings Manager [NEW]
│   │
│   ├── 2.4.1 Чтение настроек
│   │   ├── get_plugin_settings(plugin_id) → dict
│   │   ├── get_setting(plugin_id, key) → any
│   │   └── Дешифрование секретов (Fernet)
│   │
│   ├── 2.4.2 Запись настроек
│   │   ├── save_plugin_settings(plugin_id, settings: dict)
│   │   ├── Валидация по схеме из plugin.yaml
│   │   ├── Шифрование секретов (type: password)
│   │   └── Обновление статуса (needs_config → enabled)
│   │
│   ├── 2.4.3 Валидация
│   │   ├── Проверка required полей
│   │   ├── Проверка типов
│   │   ├── Проверка options для select
│   │   └── Возврат ошибок валидации
│   │
│   ├── 2.4.4 Статус конфигурации
│   │   ├── is_configured(plugin_id) → bool
│   │   ├── get_missing_settings(plugin_id) → List[str]
│   │   └── Автоматическое определение needs_config
│   │
│   ├── Files:
│   │   └── tools/settings_manager.py [NEW]
│   │
│   ├── Dependencies: Tools Repository, Encryption
│   │
│   └── Done when:
│       └── Настройки плагинов читаются/пишутся с шифрованием
│
├── 2.5 Plugin Base (утилиты для плагинов) [NEW]
│   │
│   ├── 2.5.1 Доступ к настройкам
│   │   ├── get_setting(key) — для использования в handlers
│   │   └── require_setting(key) — с исключением если нет
│   │
│   ├── 2.5.2 Доступ к LLM (для плагинов с uses_llm)
│   │   ├── get_llm_client() → LLMClient
│   │   ├── generate(prompt) → str
│   │   └── Использование главного LLM или отдельного
│   │
│   ├── 2.5.3 HTTP клиент
│   │   ├── get_http_client() → httpx.AsyncClient
│   │   └── Преднастроенный с таймаутами
│   │
│   ├── 2.5.4 Логирование
│   │   ├── get_logger(plugin_id) → Logger
│   │   └── Префикс [plugin_id] в логах
│   │
│   ├── Files:
│   │   └── tools/base.py [NEW]
│   │
│   ├── Dependencies: Settings Manager, LLM Engine
│   │
│   └── Done when:
│       └── Плагины могут использовать утилиты через import
```

---

## 3. STORAGE — EXTENSION

```
3. STORAGE
│
├── 3.1 Модели данных [NEW]
│   │
│   ├── 3.1.1 ToolSettingsModel
│   │   ├── tool_name: str (PK)
│   │   ├── plugin_id: str
│   │   ├── enabled: bool (default False)
│   │   ├── settings_json: str (encrypted JSON)
│   │   ├── created_at: datetime
│   │   └── updated_at: datetime
│   │
│   ├── 3.1.2 ToolCallLogModel (optional)
│   │   ├── id: int (PK, autoincrement)
│   │   ├── tool_name: str
│   │   ├── user_id: str (telegram user id)
│   │   ├── chat_id: str
│   │   ├── params_json: str
│   │   ├── result_json: str
│   │   ├── success: bool
│   │   ├── duration_ms: int
│   │   └── created_at: datetime
│   │
│   ├── Files:
│   │   └── api/db.py [EXTENSION]
│   │
│   ├── Dependencies: SQLAlchemy
│   │
│   └── Done when:
│       └── Таблицы создаются при старте, миграция не ломает существующие
│
├── 3.2 Tools Repository [NEW]
│   │
│   ├── 3.2.1 CRUD операции
│   │   ├── get_tool_settings(tool_name) → ToolSettingsModel | None
│   │   ├── get_all_tool_settings() → List[ToolSettingsModel]
│   │   ├── save_tool_settings(tool_name, plugin_id, enabled, settings)
│   │   ├── update_tool_enabled(tool_name, enabled)
│   │   └── delete_tool_settings(tool_name)
│   │
│   ├── 3.2.2 Шифрование
│   │   ├── encrypt_settings(settings: dict) → str
│   │   ├── decrypt_settings(encrypted: str) → dict
│   │   └── Использование существующего encryption.py
│   │
│   ├── 3.2.3 Маскирование для API
│   │   ├── mask_settings(settings: dict, schema: List) → dict
│   │   ├── Маскирование полей type: password
│   │   └── Формат: "***{last_5_chars}"
│   │
│   ├── Files:
│   │   └── api/tools_repository.py [NEW]
│   │
│   ├── Dependencies: db.py, encryption.py
│   │
│   └── Done when:
│       └── CRUD работает, секреты шифруются как TG/LLM
```

---

## 4. ADMIN API — EXTENSION

```
4. ADMIN API
│
├── 4.1 Tools Router [NEW]
│   │
│   ├── 4.1.1 GET /api/tools
│   │   ├── Список всех инструментов
│   │   ├── Данные из Registry + статусы из БД
│   │   ├── Response: [{name, description, plugin_id, enabled, needs_config}]
│   │   └── Авторизация: X-Admin-Key
│   │
│   ├── 4.1.2 GET /api/tools/{name}
│   │   ├── Детали инструмента
│   │   ├── Включает: description, parameters, settings schema
│   │   ├── Response: {name, description, parameters, settings_schema, current_settings (masked)}
│   │   └── 404 если не найден
│   │
│   ├── 4.1.3 POST /api/tools/{name}/enable
│   │   ├── Включить инструмент
│   │   ├── Проверка: настройки заполнены (если required)
│   │   ├── Response: {success, message}
│   │   └── 400 если needs_config
│   │
│   ├── 4.1.4 POST /api/tools/{name}/disable
│   │   ├── Выключить инструмент
│   │   ├── Response: {success}
│   │   └── Всегда успешно
│   │
│   ├── 4.1.5 GET /api/tools/{name}/settings
│   │   ├── Получить настройки (masked)
│   │   ├── Response: {settings: {...}, schema: [...]}
│   │   └── Пароли маскированы
│   │
│   ├── 4.1.6 PUT /api/tools/{name}/settings
│   │   ├── Сохранить настройки
│   │   ├── Body: {settings: {...}}
│   │   ├── Валидация по схеме
│   │   ├── Response: {success, errors?}
│   │   └── 400 при ошибках валидации
│   │
│   ├── 4.1.7 POST /api/tools/{name}/test
│   │   ├── Проверить подключение (если есть внешний API)
│   │   ├── Вызов специального test handler (optional)
│   │   ├── Response: {success, message, details?}
│   │   └── 400/500 при ошибке
│   │
│   ├── Files:
│   │   └── api/tools_router.py [NEW]
│   │
│   ├── Dependencies: Tool Registry, Tools Repository, Settings Manager
│   │
│   └── Done when:
│       └── Все эндпоинты работают, Swagger документация
│
├── 4.2 Plugins Router [NEW]
│   │
│   ├── 4.2.1 POST /api/plugins/reload
│   │   ├── Перезагрузить все плагины
│   │   ├── Вызов Plugin Loader.reload_all()
│   │   ├── Response: {success, loaded: [...], errors: [...]}
│   │   └── Partial success возможен
│   │
│   ├── 4.2.2 POST /api/plugins/{id}/reload
│   │   ├── Перезагрузить конкретный плагин
│   │   ├── Response: {success, message}
│   │   └── 404 если не найден
│   │
│   ├── 4.2.3 GET /api/plugins
│   │   ├── Список плагинов
│   │   ├── Response: [{id, name, version, tools_count, enabled_count}]
│   │   └── Группировка по плагинам
│   │
│   ├── Files:
│   │   └── api/plugins_router.py [NEW]
│   │
│   ├── Dependencies: Plugin Loader
│   │
│   └── Done when:
│       └── Hot-reload работает через API
│
├── 4.3 Интеграция в app.py [EXTENSION]
│   │
│   ├── 4.3.1 Подключение роутеров
│   │   ├── app.include_router(tools_router)
│   │   └── app.include_router(plugins_router)
│   │
│   ├── 4.3.2 Startup event
│   │   ├── Инициализация Plugin Loader
│   │   ├── Загрузка плагинов
│   │   └── Синхронизация Registry с БД
│   │
│   ├── Files:
│   │   └── api/app.py [EXTENSION]
│   │
│   └── Done when:
│       └── Плагины загружаются при старте приложения
```

---

## 5. ADMIN PANEL (UI) — EXTENSION

```
5. ADMIN PANEL
│
├── 5.1 Навигация [EXTENSION]
│   │
│   ├── 5.1.1 Структура меню
│   │   ├── Настройки (существующий)
│   │   ├── Инструменты (новый)
│   │   └── Администраторы (новый)
│   │
│   ├── 5.1.2 Роутинг
│   │   ├── #settings (существующий)
│   │   ├── #tools (новый)
│   │   └── #admins (новый)
│   │
│   ├── 5.1.3 Активный пункт меню
│   │   └── Подсветка текущего раздела
│   │
│   ├── Files:
│   │   ├── admin/index.html [EXTENSION]
│   │   └── admin/app.js [EXTENSION]
│   │
│   └── Done when:
│       └── Меню с 3 пунктами, переключение разделов
│
├── 5.2 Страница "Инструменты" [NEW]
│   │
│   ├── 5.2.1 Список инструментов
│   │   ├── Загрузка GET /api/tools
│   │   ├── Отображение карточек/таблицы
│   │   ├── Группировка по плагинам (optional)
│   │   └── Фильтр: все / включённые / выключенные
│   │
│   ├── 5.2.2 Карточка инструмента
│   │   ├── Название
│   │   ├── Описание
│   │   ├── Плагин (откуда)
│   │   ├── Статус (badge): Включён / Выключен / Требует настройки
│   │   └── Кнопки действий
│   │
│   ├── 5.2.3 Действия с инструментом
│   │   ├── Кнопка "Включить" → POST /api/tools/{name}/enable
│   │   ├── Кнопка "Выключить" → POST /api/tools/{name}/disable
│   │   ├── Кнопка "Настройки" → открыть модалку/страницу
│   │   └── Toast уведомления об успехе/ошибке
│   │
│   ├── 5.2.4 Форма настроек инструмента
│   │   ├── Заголовок с названием инструмента
│   │   ├── Динамическая форма из settings schema
│   │   ├── Типы полей: text, password, number, select, checkbox
│   │   ├── Маскирование паролей (показать/скрыть)
│   │   ├── Валидация на клиенте
│   │   ├── Кнопка "Проверить подключение" (если есть test)
│   │   └── Кнопки: Сохранить, Отмена
│   │
│   ├── 5.2.5 Кнопка "Перезагрузить плагины"
│   │   ├── POST /api/plugins/reload
│   │   ├── Индикатор загрузки
│   │   └── Toast с результатом
│   │
│   ├── Files:
│   │   ├── admin/index.html [EXTENSION] или admin/tools.html [NEW]
│   │   ├── admin/tools.js [NEW]
│   │   └── admin/styles.css [EXTENSION]
│   │
│   ├── Dependencies: Tools API готов
│   │
│   └── Done when:
│       └── Полное управление инструментами через UI
│
├── 5.3 Страница "Администраторы" [NEW]
│   │
│   ├── 5.3.1 Список администраторов
│   │   ├── Загрузка GET /api/service-admins
│   │   ├── Таблица: ID, Имя, Username, Дата добавления
│   │   └── Пустое состояние: "Нет администраторов"
│   │
│   ├── 5.3.2 Добавление администратора
│   │   ├── Кнопка "+ Добавить"
│   │   ├── Модалка с формой
│   │   ├── Поле: Telegram ID (number, required)
│   │   ├── Подсказка про @userinfobot
│   │   ├── POST /api/service-admins
│   │   └── Toast с результатом
│   │
│   ├── 5.3.3 Действия с администратором
│   │   ├── Кнопка "Обновить" → POST /api/service-admins/{id}/refresh
│   │   ├── Кнопка "Удалить" → модалка подтверждения
│   │   └── DELETE /api/service-admins/{id}
│   │
│   ├── 5.3.4 Модалка подтверждения удаления
│   │   ├── Текст: "Удалить администратора {имя}?"
│   │   └── Кнопки: Удалить (danger), Отмена
│   │
│   ├── Files:
│   │   ├── admin/index.html [EXTENSION] или admin/admins.html [NEW]
│   │   ├── admin/admins.js [NEW]
│   │   └── admin/styles.css [EXTENSION]
│   │
│   ├── Dependencies: API already exists!
│   │
│   └── Done when:
│       └── Полное управление админами через UI
```

---

## 6. BUILTIN PLUGINS — NEW

```
6. BUILTIN PLUGINS
│
├── 6.1 Calculator [NEW]
│   │
│   ├── 6.1.1 plugin.yaml
│   │   ├── id: calculator
│   │   ├── name: "Calculator"
│   │   ├── version: "1.0.0"
│   │   ├── enabled: true (по умолчанию)
│   │   └── tools:
│   │       └── calculate
│   │           ├── description: "Evaluates mathematical expression"
│   │           └── parameters: {expression: string}
│   │
│   ├── 6.1.2 handlers.py
│   │   ├── async def calculate(expression: str) → str
│   │   ├── Безопасный eval (без __builtins__)
│   │   ├── Поддержка: +, -, *, /, **, sqrt, sin, cos, etc.
│   │   └── Обработка ошибок (деление на 0, синтаксис)
│   │
│   ├── Files:
│   │   ├── plugins/builtin/calculator/plugin.yaml
│   │   └── plugins/builtin/calculator/handlers.py
│   │
│   ├── Settings: None
│   │
│   └── Done when:
│       └── "Посчитай 2+2*3" → "8"
│
├── 6.2 DateTime Tools [NEW]
│   │
│   ├── 6.2.1 plugin.yaml
│   │   ├── id: datetime-tools
│   │   ├── name: "Date & Time"
│   │   ├── version: "1.0.0"
│   │   ├── enabled: true
│   │   └── tools:
│   │       ├── get_current_datetime
│   │       │   └── description: "Returns current date and time"
│   │       └── get_weekday
│   │           ├── description: "Returns weekday for a date"
│   │           └── parameters: {date: string}
│   │
│   ├── 6.2.2 handlers.py
│   │   ├── async def get_current_datetime() → str
│   │   │   └── Return: "2024-01-15 14:30:00 (Monday)"
│   │   └── async def get_weekday(date: str) → str
│   │       ├── Парсинг даты (разные форматы)
│   │       └── Return: "Monday" / "Понедельник"
│   │
│   ├── Files:
│   │   ├── plugins/builtin/datetime_tools/plugin.yaml
│   │   └── plugins/builtin/datetime_tools/handlers.py
│   │
│   ├── Настройки:
│   │   └── timezone (опционально, default: UTC)
│   │
│   └── Done when:
│       └── "Сколько времени?" → текущее время
```

---

## 7. BUSINESS PLUGINS — NEW (Phase 6+)

```
7. BUSINESS PLUGINS
│
├── 7.1 Worklog Checker [PHASE 6]
│   │
│   ├── 7.1.1 plugin.yaml
│   │   ├── id: worklog-checker
│   │   ├── name: "Проверка ворклогов"
│   │   ├── version: "1.0.0"
│   │   ├── enabled: false (требует настройки)
│   │   ├── tools:
│   │   │   ├── check_worklogs
│   │   │   │   ├── description: "Checks employee worklogs..."
│   │   │   │   ├── parameters: {employee: string, period: string}
│   │   │   │   └── timeout: 60
│   │   │   └── get_worklog_summary
│   │   │       ├── description: "Gets team worklog summary"
│   │   │       └── parameters: {team: string, period: string}
│   │   └── settings:
│   │       ├── jira_url (string, required)
│   │       ├── jira_email (string, required)
│   │       ├── jira_token (password, required)
│   │       ├── tempo_token (password, required)
│   │       ├── required_hours_per_day (number, default: 8)
│   │       └── working_days (string, default: "mon,tue,wed,thu,fri")
│   │
│   ├── 7.1.2 handlers.py
│   │   ├── async def check_worklogs(employee, period) → dict
│   │   │   ├── Получение настроек
│   │   │   ├── Поиск сотрудника в Jira
│   │   │   ├── Запрос ворклогов из Tempo
│   │   │   ├── Расчёт нормы и дефицита
│   │   │   └── Return: {employee, period, logged, required, deficit, tasks}
│   │   └── async def get_worklog_summary(team, period) → dict
│   │
│   ├── 7.1.3 jira_client.py (вспомогательный)
│   │   ├── class JiraClient
│   │   ├── search_user(query) → User
│   │   ├── get_issues(user, period) → List[Issue]
│   │   └── Обработка ошибок API
│   │
│   ├── 7.1.4 tempo_client.py (вспомогательный)
│   │   ├── class TempoClient
│   │   ├── get_worklogs(user_key, date_from, date_to) → List[Worklog]
│   │   └── Обработка ошибок API
│   │
│   ├── 7.1.5 test handler (optional)
│   │   ├── async def test_connection() → dict
│   │   ├── Проверка подключения к Jira
│   │   ├── Проверка подключения к Tempo
│   │   └── Return: {jira_ok, tempo_ok, errors}
│   │
│   ├── Files:
│   │   ├── plugins/worklog_checker/plugin.yaml
│   │   ├── plugins/worklog_checker/handlers.py
│   │   ├── plugins/worklog_checker/jira_client.py
│   │   └── plugins/worklog_checker/tempo_client.py
│   │
│   ├── Dependencies: httpx, Jira API, Tempo API
│   │
│   └── Done when:
│       └── "Проверь ворклоги Иванова" → реальные данные
│
├── 7.2 HR Service [FUTURE]
│   │
│   ├── 7.2.1 Инструменты
│   │   ├── get_employee — получить данные сотрудника
│   │   ├── list_employees — список с фильтрами
│   │   ├── search_employees — поиск по имени/отделу
│   │   └── update_employee — обновить данные
│   │
│   ├── 7.2.2 Хранение
│   │   ├── Отдельная таблица employees в SQLite
│   │   └── Или интеграция с внешней HR-системой
│   │
│   ├── 7.2.3 Импорт
│   │   ├── import_from_excel — загрузка из Excel
│   │   └── import_from_csv — загрузка из CSV
│   │
│   └── Done when:
│       └── "Кто руководитель Иванова?" → ответ из базы
│
├── 7.3 Reminder [FUTURE]
│   │
│   ├── 7.3.1 Инструменты
│   │   ├── find_violators — найти нарушителей за период
│   │   ├── send_reminder — отправить напоминание (uses_llm: true)
│   │   └── escalate_to_manager — эскалация руководителю
│   │
│   ├── 7.3.2 LLM интеграция
│   │   ├── Генерация персонализированного текста
│   │   ├── Настраиваемый тон (friendly/formal/strict)
│   │   └── Промпты в templates.py
│   │
│   ├── 7.3.3 Scheduler интеграция
│   │   ├── Крон-задача: проверка нарушителей
│   │   ├── Автоматическая отправка напоминаний
│   │   └── Эскалация по таймауту
│   │
│   └── Done when:
│       └── Автоматические напоминания с персонализацией
```

---

## Summary table of all components

| # | Block | Subblock | Type | Phase | Files |
|---|-------|----------|------|-------|-------|
| 1.1 | LLM Engine | LLM Router | New | 1 | bot/tool_calling.py |
| 1.2 | LLM Engine | Provider Adapter | Extension | 1 | bot/llm.py |
| 2.1 | Plugin System | Tool Registry | New | 2 | tools/registry.py, models.py |
| 2.2 | Plugin System | Plugin Loader | New | 2 | tools/loader.py |
| 2.3 | Plugin System | Tool Executor | New | 2 | tools/executor.py |
| 2.4 | Plugin System | Settings Manager | New | 3 | tools/settings_manager.py |
| 2.5 | Plugin System | Plugin Base | New | 2 | tools/base.py |
| 3.1 | Storage | Data models | New | 3 | api/db.py |
| 3.2 | Storage | Tools Repository | New | 3 | api/tools_repository.py |
| 4.1 | Admin API | Tools Router | New | 3 | api/tools_router.py |
| 4.2 | Admin API | Plugins Router | New | 3 | api/plugins_router.py |
| 4.3 | Admin API | Integration | Extension | 3 | api/app.py |
| 5.1 | Admin Panel | Navigation | Extension | 4 | admin/index.html, app.js |
| 5.2 | Admin Panel | Tools | New | 4 | admin/tools.js |
| 5.3 | Admin Panel | Administrators | New | 5 | admin/admins.js |
| 6.1 | Builtin Plugins | Calculator | New | 2 | plugins/builtin/calculator/* |
| 6.2 | Builtin Plugins | DateTime | New | 2 | plugins/builtin/datetime_tools/* |
| 7.1 | Business Plugins | Worklog Checker | New | 6 | plugins/worklog_checker/* |
| 7.2 | Business Plugins | HR Service | New | 7+ | plugins/hr_service/* |
| 7.3 | Business Plugins | Reminder | New | 7+ | plugins/reminder/* |

---

## Phase breakdown

### Phase 0: Stabilization (1–2 days)
- [ ] Review current tests
- [ ] Tag working state
- [ ] Create branch for work

### Phase 1: Tool-calling in LLM (3–5 days)
- [ ] 1.1 LLM Router
- [ ] 1.2 LLM Provider Adapter (extension)
- [ ] Tool-calling tests

### Phase 2: Plugin System (5–7 days)
- [ ] 2.1 Tool Registry
- [ ] 2.2 Plugin Loader
- [ ] 2.3 Tool Executor
- [ ] 2.5 Plugin Base
- [ ] 6.1 Calculator plugin
- [ ] 6.2 DateTime plugin
- [ ] Plugin system tests

### Phase 3: Storage + API (3–5 days)
- [ ] 3.1 Data models
- [ ] 3.2 Tools Repository
- [ ] 2.4 Settings Manager
- [ ] 4.1 Tools Router
- [ ] 4.2 Plugins Router
- [ ] 4.3 Integration in app.py
- [ ] API tests

### Phase 4: Admin "Tools" (5–7 days)
- [ ] 5.1 Navigation (extension)
- [ ] 5.2 "Tools" page
- [ ] Manual UI testing

### Phase 5: Admin "Administrators" (3–5 days)
- [ ] 5.3 "Administrators" page
- [ ] Manual UI testing

**Note:** Phase 5 can run in parallel with Phases 3–4

### Phase 6: Worklog Checker (1–2 weeks)
- [ ] 7.1 Worklog Checker plugin
- [ ] Jira API integration
- [ ] Tempo API integration
- [ ] E2E testing

### Phase 7+: Future plugins
- [ ] 7.2 HR Service
- [ ] 7.3 Reminder
- [ ] Others as needed

---

## Effort estimate

| Phase | Description | Estimate |
|-------|-------------|----------|
| 0 | Stabilization | 1–2 days |
| 1 | Tool-calling | 3–5 days |
| 2 | Plugin System | 5–7 days |
| 3 | Storage + API | 3–5 days |
| 4 | Admin "Tools" | 5–7 days |
| 5 | Admin "Administrators" | 3–5 days |
| 6 | Worklog Checker | 1–2 weeks |
| **Total to MVP** | Phases 0–6 | **6–8 weeks** |

---

## Document versioning

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-02-06 | First version of task breakdown |
