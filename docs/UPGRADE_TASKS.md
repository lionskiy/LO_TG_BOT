# UPGRADE TASKS — LO_TG_BOT

> **Декомпозиция задач по развитию проекта**  
> Детализация на 3-4 уровня для планирования и трекинга

**Версия:** 1.1  
**Дата:** 2026-02-06

---

## Связанные документы

| Документ | Описание | Статус |
|----------|----------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Целевая архитектура системы | ✅ Актуален (не завершено) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Декомпозиция задач (этот документ) | ✅ Актуален (не завершено) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Детальный план Фазы 0-1 | ✅ Актуален (не завершено) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Детальный план Фазы 2 (Plugin System) | ✅ Актуален (не завершено) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Детальный план Фазы 3 (Storage + API) | ✅ Актуален (не завершено) |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Детальный план Фазы 4 (Админка Инструменты) | ✅ Актуален (не завершено) |
| [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Детальный план Фазы 5 (Админка Администраторы) | ✅ Актуален (не завершено) |
| [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Детальный план Фазы 6 (Worklog Checker) | ✅ Актуален (не завершено) |

### Существующая документация проекта

| Документ | Описание |
|----------|----------|
| [CURRENT_IMPLEMENTATION.md](CURRENT_IMPLEMENTATION.md) | Текущая реализация (до изменений) |
| [APP_DESCRIPTION_AND_API.md](APP_DESCRIPTION_AND_API.md) | Описание приложения и API |
| [LAUNCH_INSTRUCTIONS.md](LAUNCH_INSTRUCTIONS.md) | Инструкции по запуску |

---

## Как использовать этот документ

1. **При планировании спринта** — выбираешь блок/подблок из нужной фазы
2. **При разработке** — сверяешься с критериями готовности
3. **При code review** — проверяешь что все подпункты выполнены
4. **При тестировании** — используешь критерии готовности как чеклист
5. **Детальный план фазы** — смотри соответствующий PLAN_PHASE_X.md
6. **Архитектурные вопросы** — смотри [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md)

---

## Функциональные блоки (полная декомпозиция)

---

## 1. LLM ENGINE (Оркестратор) — ДОРАБОТКА

```
1. LLM ENGINE
│
├── 1.1 LLM Router [НОВОЕ]
│   │
│   ├── 1.1.1 Формирование запроса
│   │   ├── Сборка system_prompt (английский)
│   │   ├── Получение tools из Registry
│   │   ├── Добавление истории диалога
│   │   └── Добавление сообщения пользователя
│   │
│   ├── 1.1.2 Обработка ответа LLM
│   │   ├── Проверка наличия tool_calls
│   │   ├── Парсинг function name и arguments
│   │   ├── Вызов Tool Executor
│   │   └── Формирование tool_result message
│   │
│   ├── 1.1.3 Цикл tool-calling
│   │   ├── Повторный запрос к LLM с результатом
│   │   ├── Поддержка multiple tool calls
│   │   ├── Ограничение глубины (max iterations)
│   │   └── Получение финального текстового ответа
│   │
│   ├── 1.1.4 Обработка ошибок
│   │   ├── Tool not found
│   │   ├── Tool execution error
│   │   ├── LLM timeout/error
│   │   └── Fallback к обычному ответу
│   │
│   ├── Файлы:
│   │   └── bot/tool_calling.py [НОВЫЙ]
│   │
│   ├── Зависимости: Tool Registry, Tool Executor
│   │
│   └── Критерий готовности:
│       └── LLM выбирает и вызывает инструменты, возвращает ответ
│
├── 1.2 LLM Provider Adapter [РАСШИРЕНИЕ]
│   │
│   ├── 1.2.1 OpenAI / OpenAI-compatible
│   │   ├── Добавить параметр tools в запрос
│   │   ├── Добавить параметр tool_choice
│   │   ├── Обработка response.tool_calls
│   │   └── Формирование tool result message
│   │
│   ├── 1.2.2 Anthropic (Claude)
│   │   ├── Конвертация tools в формат Anthropic
│   │   ├── Обработка tool_use blocks
│   │   └── Формирование tool_result content
│   │
│   ├── 1.2.3 Google (Gemini)
│   │   ├── Конвертация tools в формат Gemini
│   │   ├── Обработка function_call response
│   │   └── Формирование function_response
│   │
│   ├── 1.2.4 Универсальный интерфейс
│   │   ├── Абстракция ToolCall (name, arguments, id)
│   │   ├── Абстракция ToolResult (id, content)
│   │   └── Конвертеры для каждого провайдера
│   │
│   ├── Файлы:
│   │   └── bot/llm.py [РАСШИРЕНИЕ]
│   │
│   ├── Зависимости: Нет
│   │
│   └── Критерий готовности:
│       └── Tool-calling работает для OpenAI, Anthropic, Google
```

---

## 2. PLUGIN SYSTEM — НОВОЕ

```
2. PLUGIN SYSTEM
│
├── 2.1 Tool Registry [НОВОЕ]
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
│   ├── Файлы:
│   │   ├── tools/__init__.py
│   │   ├── tools/registry.py [НОВЫЙ]
│   │   └── tools/models.py [НОВЫЙ]
│   │
│   ├── Зависимости: Plugin Loader
│   │
│   └── Критерий готовности:
│       └── Registry хранит tools и формирует список для LLM
│
├── 2.2 Plugin Loader [НОВОЕ]
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
│   ├── Файлы:
│   │   └── tools/loader.py [НОВЫЙ]
│   │
│   ├── Зависимости: Нет
│   │
│   └── Критерий готовности:
│       └── Плагины загружаются из папки при старте и по команде
│
├── 2.3 Tool Executor [НОВОЕ]
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
│   ├── Файлы:
│   │   └── tools/executor.py [НОВЫЙ]
│   │
│   ├── Зависимости: Tool Registry
│   │
│   └── Критерий готовности:
│       └── Executor вызывает handlers и возвращает результат
│
├── 2.4 Plugin Settings Manager [НОВОЕ]
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
│   ├── Файлы:
│   │   └── tools/settings_manager.py [НОВЫЙ]
│   │
│   ├── Зависимости: Tools Repository, Encryption
│   │
│   └── Критерий готовности:
│       └── Настройки плагинов читаются/пишутся с шифрованием
│
├── 2.5 Plugin Base (утилиты для плагинов) [НОВОЕ]
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
│   ├── Файлы:
│   │   └── tools/base.py [НОВЫЙ]
│   │
│   ├── Зависимости: Settings Manager, LLM Engine
│   │
│   └── Критерий готовности:
│       └── Плагины могут использовать утилиты через import
```

---

## 3. STORAGE — РАСШИРЕНИЕ

```
3. STORAGE
│
├── 3.1 Модели данных [НОВОЕ]
│   │
│   ├── 3.1.1 ToolSettingsModel
│   │   ├── tool_name: str (PK)
│   │   ├── plugin_id: str
│   │   ├── enabled: bool (default False)
│   │   ├── settings_json: str (encrypted JSON)
│   │   ├── created_at: datetime
│   │   └── updated_at: datetime
│   │
│   ├── 3.1.2 ToolCallLogModel (опционально)
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
│   ├── Файлы:
│   │   └── api/db.py [РАСШИРЕНИЕ]
│   │
│   ├── Зависимости: SQLAlchemy
│   │
│   └── Критерий готовности:
│       └── Таблицы создаются при старте, миграция не ломает существующие
│
├── 3.2 Tools Repository [НОВОЕ]
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
│   ├── Файлы:
│   │   └── api/tools_repository.py [НОВЫЙ]
│   │
│   ├── Зависимости: db.py, encryption.py
│   │
│   └── Критерий готовности:
│       └── CRUD работает, секреты шифруются как TG/LLM
```

---

## 4. ADMIN API — РАСШИРЕНИЕ

```
4. ADMIN API
│
├── 4.1 Tools Router [НОВОЕ]
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
│   │   ├── Вызов специального test handler (опционально)
│   │   ├── Response: {success, message, details?}
│   │   └── 400/500 при ошибке
│   │
│   ├── Файлы:
│   │   └── api/tools_router.py [НОВЫЙ]
│   │
│   ├── Зависимости: Tool Registry, Tools Repository, Settings Manager
│   │
│   └── Критерий готовности:
│       └── Все эндпоинты работают, Swagger документация
│
├── 4.2 Plugins Router [НОВОЕ]
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
│   ├── Файлы:
│   │   └── api/plugins_router.py [НОВЫЙ]
│   │
│   ├── Зависимости: Plugin Loader
│   │
│   └── Критерий готовности:
│       └── Hot-reload работает через API
│
├── 4.3 Интеграция в app.py [РАСШИРЕНИЕ]
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
│   ├── Файлы:
│   │   └── api/app.py [РАСШИРЕНИЕ]
│   │
│   └── Критерий готовности:
│       └── Плагины загружаются при старте приложения
```

---

## 5. ADMIN PANEL (UI) — РАСШИРЕНИЕ

```
5. ADMIN PANEL
│
├── 5.1 Навигация [ДОРАБОТКА]
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
│   ├── Файлы:
│   │   ├── admin/index.html [РАСШИРЕНИЕ]
│   │   └── admin/app.js [РАСШИРЕНИЕ]
│   │
│   └── Критерий готовности:
│       └── Меню с 3 пунктами, переключение разделов
│
├── 5.2 Страница "Инструменты" [НОВОЕ]
│   │
│   ├── 5.2.1 Список инструментов
│   │   ├── Загрузка GET /api/tools
│   │   ├── Отображение карточек/таблицы
│   │   ├── Группировка по плагинам (опционально)
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
│   ├── Файлы:
│   │   ├── admin/index.html [РАСШИРЕНИЕ] или admin/tools.html [НОВЫЙ]
│   │   ├── admin/tools.js [НОВЫЙ]
│   │   └── admin/styles.css [РАСШИРЕНИЕ]
│   │
│   ├── Зависимости: Tools API готов
│   │
│   └── Критерий готовности:
│       └── Полное управление инструментами через UI
│
├── 5.3 Страница "Администраторы" [НОВОЕ]
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
│   ├── Файлы:
│   │   ├── admin/index.html [РАСШИРЕНИЕ] или admin/admins.html [НОВЫЙ]
│   │   ├── admin/admins.js [НОВЫЙ]
│   │   └── admin/styles.css [РАСШИРЕНИЕ]
│   │
│   ├── Зависимости: API уже существует!
│   │
│   └── Критерий готовности:
│       └── Полное управление админами через UI
```

---

## 6. BUILTIN PLUGINS — НОВОЕ

```
6. BUILTIN PLUGINS
│
├── 6.1 Calculator [НОВОЕ]
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
│   ├── Файлы:
│   │   ├── plugins/builtin/calculator/plugin.yaml
│   │   └── plugins/builtin/calculator/handlers.py
│   │
│   ├── Настройки: Нет
│   │
│   └── Критерий готовности:
│       └── "Посчитай 2+2*3" → "8"
│
├── 6.2 DateTime Tools [НОВОЕ]
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
│   ├── Файлы:
│   │   ├── plugins/builtin/datetime_tools/plugin.yaml
│   │   └── plugins/builtin/datetime_tools/handlers.py
│   │
│   ├── Настройки:
│   │   └── timezone (опционально, default: UTC)
│   │
│   └── Критерий готовности:
│       └── "Сколько времени?" → текущее время
```

---

## 7. BUSINESS PLUGINS — НОВОЕ (Фаза 6+)

```
7. BUSINESS PLUGINS
│
├── 7.1 Worklog Checker [ФАЗА 6]
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
│   ├── 7.1.5 test handler (опционально)
│   │   ├── async def test_connection() → dict
│   │   ├── Проверка подключения к Jira
│   │   ├── Проверка подключения к Tempo
│   │   └── Return: {jira_ok, tempo_ok, errors}
│   │
│   ├── Файлы:
│   │   ├── plugins/worklog_checker/plugin.yaml
│   │   ├── plugins/worklog_checker/handlers.py
│   │   ├── plugins/worklog_checker/jira_client.py
│   │   └── plugins/worklog_checker/tempo_client.py
│   │
│   ├── Зависимости: httpx, Jira API, Tempo API
│   │
│   └── Критерий готовности:
│       └── "Проверь ворклоги Иванова" → реальные данные
│
├── 7.2 HR Service [БУДУЩЕЕ]
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
│   └── Критерий готовности:
│       └── "Кто руководитель Иванова?" → ответ из базы
│
├── 7.3 Reminder [БУДУЩЕЕ]
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
│   └── Критерий готовности:
│       └── Автоматические напоминания с персонализацией
```

---

## Сводная таблица всех компонентов

| # | Блок | Подблок | Тип | Фаза | Файлы |
|---|------|---------|-----|------|-------|
| 1.1 | LLM Engine | LLM Router | Новое | 1 | bot/tool_calling.py |
| 1.2 | LLM Engine | Provider Adapter | Расширение | 1 | bot/llm.py |
| 2.1 | Plugin System | Tool Registry | Новое | 2 | tools/registry.py, models.py |
| 2.2 | Plugin System | Plugin Loader | Новое | 2 | tools/loader.py |
| 2.3 | Plugin System | Tool Executor | Новое | 2 | tools/executor.py |
| 2.4 | Plugin System | Settings Manager | Новое | 3 | tools/settings_manager.py |
| 2.5 | Plugin System | Plugin Base | Новое | 2 | tools/base.py |
| 3.1 | Storage | Модели данных | Новое | 3 | api/db.py |
| 3.2 | Storage | Tools Repository | Новое | 3 | api/tools_repository.py |
| 4.1 | Admin API | Tools Router | Новое | 3 | api/tools_router.py |
| 4.2 | Admin API | Plugins Router | Новое | 3 | api/plugins_router.py |
| 4.3 | Admin API | Интеграция | Расширение | 3 | api/app.py |
| 5.1 | Admin Panel | Навигация | Доработка | 4 | admin/index.html, app.js |
| 5.2 | Admin Panel | Инструменты | Новое | 4 | admin/tools.js |
| 5.3 | Admin Panel | Администраторы | Новое | 5 | admin/admins.js |
| 6.1 | Builtin Plugins | Calculator | Новое | 2 | plugins/builtin/calculator/* |
| 6.2 | Builtin Plugins | DateTime | Новое | 2 | plugins/builtin/datetime_tools/* |
| 7.1 | Business Plugins | Worklog Checker | Новое | 6 | plugins/worklog_checker/* |
| 7.2 | Business Plugins | HR Service | Новое | 7+ | plugins/hr_service/* |
| 7.3 | Business Plugins | Reminder | Новое | 7+ | plugins/reminder/* |

---

## Распределение по фазам

### Фаза 0: Стабилизация (1-2 дня)
- [ ] Ревью текущих тестов
- [ ] Фиксация рабочего состояния (tag)
- [ ] Создание ветки для работ

### Фаза 1: Tool-calling в LLM (3-5 дней)
- [ ] 1.1 LLM Router
- [ ] 1.2 LLM Provider Adapter (расширение)
- [ ] Тесты tool-calling

### Фаза 2: Plugin System (5-7 дней)
- [ ] 2.1 Tool Registry
- [ ] 2.2 Plugin Loader
- [ ] 2.3 Tool Executor
- [ ] 2.5 Plugin Base
- [ ] 6.1 Calculator plugin
- [ ] 6.2 DateTime plugin
- [ ] Тесты plugin system

### Фаза 3: Storage + API (3-5 дней)
- [ ] 3.1 Модели данных
- [ ] 3.2 Tools Repository
- [ ] 2.4 Settings Manager
- [ ] 4.1 Tools Router
- [ ] 4.2 Plugins Router
- [ ] 4.3 Интеграция в app.py
- [ ] Тесты API

### Фаза 4: Админка "Инструменты" (5-7 дней)
- [ ] 5.1 Навигация (доработка)
- [ ] 5.2 Страница "Инструменты"
- [ ] Ручное тестирование UI

### Фаза 5: Админка "Администраторы" (3-5 дней)
- [ ] 5.3 Страница "Администраторы"
- [ ] Ручное тестирование UI

**Примечание:** Фаза 5 может выполняться параллельно с Фазами 3-4

### Фаза 6: Worklog Checker (1-2 недели)
- [ ] 7.1 Worklog Checker plugin
- [ ] Интеграция Jira API
- [ ] Интеграция Tempo API
- [ ] E2E тестирование

### Фаза 7+: Будущие плагины
- [ ] 7.2 HR Service
- [ ] 7.3 Reminder
- [ ] Другие по необходимости

---

## Оценка трудозатрат

| Фаза | Описание | Оценка |
|------|----------|--------|
| 0 | Стабилизация | 1-2 дня |
| 1 | Tool-calling | 3-5 дней |
| 2 | Plugin System | 5-7 дней |
| 3 | Storage + API | 3-5 дней |
| 4 | Админка "Инструменты" | 5-7 дней |
| 5 | Админка "Администраторы" | 3-5 дней |
| 6 | Worklog Checker | 1-2 недели |
| **Итого до MVP** | Фазы 0-6 | **6-8 недель** |

---

## Версионирование документа

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0 | 2026-02-06 | Первая версия декомпозиции задач |
