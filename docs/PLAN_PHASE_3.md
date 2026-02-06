# PHASE 3: Storage + API

> **Детальная постановка задач для Фазы 3**  
> Сохранение настроек плагинов в БД и API для управления инструментами

**Версия:** 1.0  
**Дата:** 2026-02-06  
**Ориентировочный срок:** 3-5 дней  
**Предусловие:** Фаза 2 завершена (Plugin System работает)

---

## Связанные документы

| Документ | Описание | Статус |
|----------|----------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Целевая архитектура системы | ✅ Актуален |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Декомпозиция всех задач | ✅ Актуален |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Детальный план Фазы 0-1 | ✅ Завершён |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Детальный план Фазы 2 | ✅ Завершён |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Детальный план Фазы 3 (этот документ) | ✅ Актуален |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Детальный план Фазы 4 (следующая) | ✅ Актуален |

### Существующая документация проекта

| Документ | Описание |
|----------|----------|
| [CURRENT_IMPLEMENTATION.md](CURRENT_IMPLEMENTATION.md) | Текущая реализация |
| [APP_DESCRIPTION_AND_API.md](APP_DESCRIPTION_AND_API.md) | Описание приложения и API |

---

## Навигация по фазам

| Фаза | Документ | Описание | Статус |
|------|----------|----------|--------|
| 0-1 | [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Стабилизация + Tool-Calling | ✅ Завершён |
| 2 | [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Plugin System | ✅ Завершён |
| 3 | **[PLAN_PHASE_3.md](PLAN_PHASE_3.md)** | Storage + API | 📍 Текущий |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Админка Инструменты | ✅ Следующий |
| 5 | [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Админка Администраторы | 📋 Планируется |
| 6 | [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Worklog Checker | 📋 Планируется |

---

## Общая цель Фазы 3

**Было (после Фазы 2):** Plugin System работает, но настройки плагинов не сохраняются. При перезапуске всё сбрасывается.

**Стало:** Настройки плагинов (enabled/disabled, credentials, параметры) сохраняются в БД. Есть API для управления инструментами и их настройками.

**Важно:** 
- Используем существующую инфраструктуру (SQLite, encryption.py)
- API защищён X-Admin-Key (как существующие эндпоинты)
- Секреты шифруются (Fernet, как Telegram/LLM токены)

---

## Архитектура Фазы 3

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Admin Panel (Фаза 4)                                                       │
│       │                                                                     │
│       │  HTTP                                                               │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │  Admin API (FastAPI)                                                    │
│  │                                                                         │
│  │  Существующие роутеры:                                                  │
│  │  ├── /api/settings/telegram/*                                          │
│  │  ├── /api/settings/llm/*                                               │
│  │  └── /api/service-admins/*                                             │
│  │                                                                         │
│  │  Новые роутеры:                              [ФАЗА 3]                   │
│  │  ├── /api/tools/*          ← tools_router.py                           │
│  │  └── /api/plugins/*        ← plugins_router.py                         │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
│       │                               │
│       │                               │
│       ▼                               ▼
│  ┌───────────────────┐      ┌───────────────────────────────────────────┐
│  │  Tools Repository │      │  Plugin Settings Manager                  │
│  │                   │      │  (tools/settings_manager.py)              │
│  │  • CRUD операции  │◄────►│                                           │
│  │  • Шифрование     │      │  • get_settings()                         │
│  │                   │      │  • save_settings()                        │
│  └───────────────────┘      │  • validate_settings()                    │
│       │                      │  • sync_with_registry()                   │
│       │                      └───────────────────────────────────────────┘
│       ▼                               │
│  ┌───────────────────┐               │
│  │  SQLite           │               │
│  │                   │               ▼
│  │  tool_settings    │      ┌───────────────────────────────────────────┐
│  │  ├── tool_name    │      │  Tool Registry (из Фазы 2)                │
│  │  ├── plugin_id    │      │                                           │
│  │  ├── enabled      │◄────►│  • Синхронизация enabled статусов        │
│  │  ├── settings_json│      │  • Получение schema для валидации        │
│  │  └── updated_at   │      │                                           │
│  │                   │      └───────────────────────────────────────────┘
│  └───────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Новые/изменяемые файлы

```
LO_TG_BOT/
├── api/
│   ├── db.py                   # [РАСШИРЕНИЕ] Добавить ToolSettingsModel
│   ├── tools_repository.py     # [НОВЫЙ] CRUD для tool_settings
│   ├── tools_router.py         # [НОВЫЙ] API /api/tools/*
│   ├── plugins_router.py       # [НОВЫЙ] API /api/plugins/*
│   └── app.py                  # [РАСШИРЕНИЕ] Подключить роутеры, startup
│
├── tools/
│   └── settings_manager.py     # [РАСШИРЕНИЕ] Интеграция с БД
│
└── tests/
    ├── test_tools_repository.py
    ├── test_tools_router.py
    └── test_plugins_router.py
```

---

# Задачи Фазы 3

---

## Задача 3.1: Модель данных ToolSettingsModel

### Описание
Добавить SQLAlchemy модель для хранения настроек инструментов в существующую БД.

### Файл: api/db.py (расширение)

### Модель ToolSettingsModel

```python
class ToolSettingsModel(Base):
    """
    Настройки инструмента/плагина.
    
    Хранит:
    - Статус включения (enabled)
    - Настройки плагина (settings_json) — зашифрованы
    """
    __tablename__ = "tool_settings"
    
    # Первичный ключ — имя инструмента
    tool_name = Column(String, primary_key=True)
    
    # ID плагина-владельца (для группировки)
    plugin_id = Column(String, nullable=False, index=True)
    
    # Включён ли инструмент
    enabled = Column(Boolean, default=False, nullable=False)
    
    # Настройки в JSON (зашифрованы Fernet)
    # Формат: {"jira_url": "...", "jira_token": "..."}
    settings_json = Column(Text, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Миграция

Таблица создаётся автоматически при старте (как существующие таблицы):

```python
# В init_db() или create_tables()
Base.metadata.create_all(bind=engine)
```

**Важно:** Существующие таблицы (telegram_settings, llm_settings, service_admins) не затрагиваются.

### Индексы

```python
# Индекс для быстрого поиска по plugin_id
Index('ix_tool_settings_plugin_id', ToolSettingsModel.plugin_id)
```

### Критерий готовности
- [ ] Модель добавлена в api/db.py
- [ ] Таблица создаётся при старте
- [ ] Существующие таблицы не ломаются
- [ ] Тест на создание/чтение записи

---

## Задача 3.2: Tools Repository

### Описание
Слой доступа к данным для tool_settings. Инкапсулирует CRUD операции и шифрование.

### Файл: api/tools_repository.py (новый)

### Функции

#### Чтение
```python
def get_tool_settings(tool_name: str) -> ToolSettingsModel | None:
    """
    Получить настройки инструмента по имени.
    
    Args:
        tool_name: Имя инструмента
        
    Returns:
        Модель с расшифрованными настройками или None
    """

def get_all_tool_settings() -> List[ToolSettingsModel]:
    """
    Получить настройки всех инструментов.
    
    Returns:
        Список моделей (настройки расшифрованы)
    """

def get_tool_settings_by_plugin(plugin_id: str) -> List[ToolSettingsModel]:
    """
    Получить настройки инструментов конкретного плагина.
    """
```

#### Запись
```python
def save_tool_settings(
    tool_name: str,
    plugin_id: str,
    enabled: bool = False,
    settings: dict | None = None
) -> ToolSettingsModel:
    """
    Сохранить настройки инструмента (create or update).
    
    Args:
        tool_name: Имя инструмента
        plugin_id: ID плагина
        enabled: Включён ли
        settings: Словарь настроек (будет зашифрован)
        
    Returns:
        Сохранённая модель
    """

def update_tool_enabled(tool_name: str, enabled: bool) -> bool:
    """
    Обновить только статус enabled.
    
    Returns:
        True если успешно, False если не найден
    """

def update_tool_settings(tool_name: str, settings: dict) -> bool:
    """
    Обновить только настройки (без изменения enabled).
    
    Returns:
        True если успешно, False если не найден
    """
```

#### Удаление
```python
def delete_tool_settings(tool_name: str) -> bool:
    """
    Удалить настройки инструмента.
    
    Returns:
        True если удалено, False если не найдено
    """

def delete_plugin_settings(plugin_id: str) -> int:
    """
    Удалить настройки всех инструментов плагина.
    
    Returns:
        Количество удалённых записей
    """
```

### Шифрование

Используем существующий `api/encryption.py`:

```python
from api.encryption import encrypt_value, decrypt_value

def _encrypt_settings(settings: dict) -> str:
    """Зашифровать настройки в JSON строку"""
    json_str = json.dumps(settings, ensure_ascii=False)
    return encrypt_value(json_str)

def _decrypt_settings(encrypted: str) -> dict:
    """Расшифровать настройки из JSON строки"""
    json_str = decrypt_value(encrypted)
    return json.loads(json_str)
```

### Маскирование для API

```python
def mask_settings(
    settings: dict, 
    schema: List[PluginSettingDefinition]
) -> dict:
    """
    Маскировать секретные поля для отдачи в API.
    
    Поля с type='password' маскируются как '***xxxxx' (последние 5 символов).
    
    Args:
        settings: Расшифрованные настройки
        schema: Схема настроек из plugin.yaml
        
    Returns:
        Настройки с замаскированными паролями
    """
    
def _mask_value(value: str) -> str:
    """Маскирует значение, оставляя последние 5 символов"""
    if not value or len(value) <= 5:
        return "***"
    return f"***{value[-5:]}"
```

### Работа с сессиями

Использовать паттерн из существующего кода:

```python
from api.db import SessionLocal

def get_tool_settings(tool_name: str) -> ToolSettingsModel | None:
    with SessionLocal() as session:
        result = session.query(ToolSettingsModel).filter(
            ToolSettingsModel.tool_name == tool_name
        ).first()
        
        if result and result.settings_json:
            # Расшифровываем перед возвратом
            result._decrypted_settings = _decrypt_settings(result.settings_json)
        
        return result
```

### Критерий готовности
- [ ] Все CRUD функции реализованы
- [ ] Шифрование работает (используется encryption.py)
- [ ] Маскирование работает
- [ ] Тесты на все операции
- [ ] Тесты на шифрование/расшифровку

---

## Задача 3.3: Plugin Settings Manager (расширение)

### Описание
Расширить `tools/settings_manager.py` для работы с БД вместо заглушек.

### Файл: tools/settings_manager.py (расширение из Фазы 2)

### Было (Фаза 2)

```python
def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    # Заглушка — всегда возвращает default
    return default
```

### Стало (Фаза 3)

```python
from api.tools_repository import get_tool_settings, save_tool_settings

def get_plugin_settings(plugin_id: str) -> dict:
    """
    Получить все настройки плагина из БД.
    
    Args:
        plugin_id: ID плагина
        
    Returns:
        Словарь настроек или пустой dict
    """
    # Получаем настройки первого инструмента плагина
    # (все инструменты плагина используют общие настройки)
    from tools import get_registry
    registry = get_registry()
    
    tools = registry.get_tools_by_plugin(plugin_id)
    if not tools:
        return {}
    
    tool_name = tools[0].name
    record = get_tool_settings(tool_name)
    
    if record and hasattr(record, '_decrypted_settings'):
        return record._decrypted_settings
    
    return {}


def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    """
    Получить конкретную настройку плагина.
    """
    settings = get_plugin_settings(plugin_id)
    return settings.get(key, default)


def save_plugin_settings(plugin_id: str, settings: dict) -> None:
    """
    Сохранить настройки плагина.
    Сохраняет для всех инструментов плагина.
    """
    from tools import get_registry
    registry = get_registry()
    
    tools = registry.get_tools_by_plugin(plugin_id)
    
    for tool in tools:
        save_tool_settings(
            tool_name=tool.name,
            plugin_id=plugin_id,
            enabled=tool.enabled,
            settings=settings
        )


def is_plugin_configured(plugin_id: str) -> bool:
    """
    Проверить что все обязательные настройки заполнены.
    """
    from tools import get_registry
    registry = get_registry()
    
    manifest = registry.get_plugin(plugin_id)
    if not manifest or not manifest.settings:
        return True  # Нет настроек — считаем настроенным
    
    settings = get_plugin_settings(plugin_id)
    
    for setting_def in manifest.settings:
        if setting_def.required:
            value = settings.get(setting_def.key)
            if value is None or value == "":
                return False
    
    return True


def get_missing_settings(plugin_id: str) -> List[str]:
    """
    Получить список незаполненных обязательных настроек.
    """
    from tools import get_registry
    registry = get_registry()
    
    manifest = registry.get_plugin(plugin_id)
    if not manifest or not manifest.settings:
        return []
    
    settings = get_plugin_settings(plugin_id)
    missing = []
    
    for setting_def in manifest.settings:
        if setting_def.required:
            value = settings.get(setting_def.key)
            if value is None or value == "":
                missing.append(setting_def.key)
    
    return missing


def validate_plugin_settings(settings: dict, schema: List) -> List[dict]:
    """
    Валидировать настройки по схеме.
    
    Returns:
        Список ошибок [{"field": "...", "error": "..."}] или []
    """
    errors = []
    
    for setting_def in schema:
        key = setting_def.key
        value = settings.get(key)
        
        # Проверка required
        if setting_def.required and (value is None or value == ""):
            # Пропускаем замаскированные пароли
            if not (isinstance(value, str) and value.startswith("***")):
                errors.append({"field": key, "error": "Required field is empty"})
                continue
        
        # Проверка типа
        if value is not None and value != "":
            if setting_def.type == "number":
                if not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except:
                        errors.append({"field": key, "error": "Must be a number"})
            
            elif setting_def.type == "boolean":
                if not isinstance(value, bool):
                    errors.append({"field": key, "error": "Must be true or false"})
    
    return errors
```

### Синхронизация с Registry

```python
async def sync_settings_with_registry() -> None:
    """
    Синхронизировать настройки из БД с Registry.
    Вызывается при старте приложения после загрузки плагинов.
    """
    from tools import get_registry
    from api.tools_repository import get_all_tool_settings
    
    registry = get_registry()
    db_settings = get_all_tool_settings()
    
    for record in db_settings:
        tool = registry.get_tool(record.tool_name)
        if tool:
            if record.enabled:
                registry.enable_tool(record.tool_name)
            else:
                registry.disable_tool(record.tool_name)
```

### Критерий готовности
- [ ] get_plugin_settings() читает из БД
- [ ] save_plugin_settings() пишет в БД
- [ ] is_plugin_configured() проверяет required поля
- [ ] validate_plugin_settings() валидирует
- [ ] sync_settings_with_registry() работает
- [ ] Тесты

---

## Задача 3.4: Tools Router (API)

### Описание
REST API для управления инструментами: список, включение/выключение, настройки.

### Файл: api/tools_router.py (новый)

### Эндпоинты

---

#### GET /api/tools — Список инструментов

**Описание:** Получить список всех инструментов с их статусами.

**Response 200:**
```json
{
  "tools": [
    {
      "name": "calculate",
      "description": "Evaluates mathematical expression...",
      "plugin_id": "calculator",
      "plugin_name": "Calculator",
      "enabled": true,
      "needs_config": false,
      "has_settings": false
    },
    {
      "name": "check_worklogs",
      "description": "Checks employee worklogs...",
      "plugin_id": "worklog-checker",
      "plugin_name": "Проверка ворклогов",
      "enabled": false,
      "needs_config": true,
      "has_settings": true
    }
  ],
  "total": 2,
  "enabled_count": 1
}
```

---

#### GET /api/tools/{name} — Детали инструмента

**Описание:** Получить полную информацию об инструменте.

**Response 200:**
```json
{
  "name": "check_worklogs",
  "description": "Checks employee worklogs for specified period",
  "plugin_id": "worklog-checker",
  "plugin_name": "Проверка ворклогов",
  "plugin_version": "1.0.0",
  "enabled": false,
  "needs_config": true,
  "parameters": {
    "type": "object",
    "properties": {
      "employee": {"type": "string", "description": "Employee name"},
      "period": {"type": "string", "description": "Period (week, month)"}
    },
    "required": ["employee"]
  },
  "settings_schema": [
    {
      "key": "jira_url",
      "label": "Jira URL",
      "type": "string",
      "required": true,
      "description": "Base URL of Jira instance"
    },
    {
      "key": "jira_token",
      "label": "Jira API Token",
      "type": "password",
      "required": true
    }
  ],
  "current_settings": {
    "jira_url": "https://jira.company.com",
    "jira_token": "***abc12"
  },
  "missing_settings": ["tempo_token"]
}
```

**Response 404:**
```json
{
  "detail": "Tool 'unknown_tool' not found"
}
```

---

#### POST /api/tools/{name}/enable — Включить инструмент

**Описание:** Включить инструмент. Проверяет что настройки заполнены.

**Response 200:**
```json
{
  "success": true,
  "message": "Tool 'calculate' enabled"
}
```

**Response 400 (нужна настройка):**
```json
{
  "success": false,
  "message": "Tool 'check_worklogs' requires configuration",
  "missing_settings": ["jira_url", "jira_token", "tempo_token"]
}
```

---

#### POST /api/tools/{name}/disable — Выключить инструмент

**Response 200:**
```json
{
  "success": true,
  "message": "Tool 'calculate' disabled"
}
```

---

#### GET /api/tools/{name}/settings — Получить настройки

**Response 200:**
```json
{
  "plugin_id": "worklog-checker",
  "settings": {
    "jira_url": "https://jira.company.com",
    "jira_token": "***abc12",
    "required_hours": 8
  },
  "schema": [...]
}
```

---

#### PUT /api/tools/{name}/settings — Сохранить настройки

**Request:**
```json
{
  "settings": {
    "jira_url": "https://jira.company.com",
    "jira_token": "new-secret-token",
    "required_hours": 8
  }
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Settings saved"
}
```

**Response 400 (ошибки валидации):**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {"field": "jira_url", "error": "Required field is empty"},
    {"field": "required_hours", "error": "Must be a number"}
  ]
}
```

**Особенность:** Если поле с type=password передано как `"***..."` (маска), оно не обновляется.

---

#### POST /api/tools/{name}/test — Тест подключения

**Response 200:**
```json
{
  "success": true,
  "message": "Connection successful",
  "details": {
    "jira": "OK",
    "tempo": "OK"
  }
}
```

**Response 400 (не поддерживается):**
```json
{
  "success": false,
  "message": "Tool 'calculate' does not support connection testing"
}
```

### Критерий готовности
- [ ] GET /api/tools работает
- [ ] GET /api/tools/{name} работает
- [ ] POST /api/tools/{name}/enable работает
- [ ] POST /api/tools/{name}/disable работает
- [ ] GET /api/tools/{name}/settings работает
- [ ] PUT /api/tools/{name}/settings работает
- [ ] POST /api/tools/{name}/test работает
- [ ] Авторизация через X-Admin-Key
- [ ] Swagger документация
- [ ] Тесты на все эндпоинты

---

## Задача 3.5: Plugins Router (API)

### Описание
API для управления плагинами: список, перезагрузка.

### Файл: api/plugins_router.py (новый)

### Эндпоинты

---

#### GET /api/plugins — Список плагинов

**Response 200:**
```json
{
  "plugins": [
    {
      "id": "calculator",
      "name": "Calculator",
      "version": "1.0.0",
      "description": "Mathematical expression evaluator",
      "tools_count": 1,
      "enabled_count": 1
    },
    {
      "id": "datetime-tools",
      "name": "Date & Time",
      "version": "1.0.0",
      "description": "Date and time utilities",
      "tools_count": 3,
      "enabled_count": 2
    }
  ],
  "total": 2
}
```

---

#### POST /api/plugins/reload — Перезагрузить все плагины

**Response 200:**
```json
{
  "success": true,
  "message": "Plugins reloaded",
  "loaded": ["calculator", "datetime-tools"],
  "failed": [],
  "total_tools": 4
}
```

---

#### POST /api/plugins/{id}/reload — Перезагрузить один плагин

**Response 200:**
```json
{
  "success": true,
  "message": "Plugin 'calculator' reloaded",
  "tools_count": 1
}
```

**Response 404:**
```json
{
  "detail": "Plugin 'unknown' not found"
}
```

### Критерий готовности
- [ ] GET /api/plugins работает
- [ ] POST /api/plugins/reload работает
- [ ] POST /api/plugins/{id}/reload работает
- [ ] Синхронизация с БД после reload
- [ ] Тесты

---

## Задача 3.6: Интеграция в app.py

### Описание
Подключить новые роутеры и настроить загрузку плагинов при старте.

### Файл: api/app.py (расширение)

### Изменения

#### Подключение роутеров

```python
from api.tools_router import router as tools_router
from api.plugins_router import router as plugins_router

# После существующих роутеров
app.include_router(tools_router)
app.include_router(plugins_router)
```

#### Startup event

```python
@app.on_event("startup")
async def startup_event():
    # Существующая логика...
    
    # НОВОЕ: Загрузка плагинов
    from tools import load_all_plugins
    from tools.settings_manager import sync_settings_with_registry
    
    logger.info("Loading plugins...")
    result = await load_all_plugins()
    logger.info(f"Loaded {len(result.loaded)} plugins with {result.total_tools} tools")
    
    if result.failed:
        for error in result.failed:
            logger.error(f"Failed to load plugin: {error.plugin_path} - {error.error}")
    
    # Синхронизируем настройки из БД
    await sync_settings_with_registry()
    logger.info("Plugin settings synchronized with database")
```

### Порядок инициализации

```
app startup:
│
├── 1. Инициализация БД (существующее)
│   └── create_tables()
│
├── 2. Загрузка плагинов (НОВОЕ)
│   ├── load_all_plugins()
│   └── Плагины регистрируются в Registry
│
├── 3. Синхронизация настроек (НОВОЕ)
│   ├── sync_settings_with_registry()
│   └── enabled статусы из БД → Registry
│
├── 4. Запуск бота (существующее)
│   └── start_bot_subprocess()
│
└── 5. Готов к приёму запросов
```

### Критерий готовности
- [ ] Роутеры подключены
- [ ] Плагины загружаются при старте
- [ ] Настройки синхронизируются
- [ ] Логирование
- [ ] Существующая функциональность не сломана

---

## Задача 3.7: Тестирование Фазы 3

### Unit-тесты

#### tests/test_tools_repository.py
```
test_save_tool_settings_new
test_save_tool_settings_update
test_get_tool_settings
test_get_tool_settings_not_found
test_get_all_tool_settings
test_update_tool_enabled
test_delete_tool_settings
test_encryption_decryption
test_mask_settings
```

#### tests/test_settings_manager.py
```
test_get_plugin_settings
test_get_plugin_setting_with_default
test_save_plugin_settings
test_is_plugin_configured_true
test_is_plugin_configured_false
test_get_missing_settings
test_validate_plugin_settings
test_sync_settings_with_registry
```

#### tests/test_tools_router.py
```
test_list_tools
test_get_tool
test_get_tool_not_found
test_enable_tool
test_enable_tool_needs_config
test_disable_tool
test_get_settings
test_update_settings
test_update_settings_validation_error
test_update_settings_preserve_masked_passwords
test_test_connection
```

#### tests/test_plugins_router.py
```
test_list_plugins
test_reload_all_plugins
test_reload_one_plugin
test_reload_one_plugin_not_found
```

### Ручное тестирование (чеклист)

**Проверка API через Swagger (/docs):**
- [ ] GET /api/tools — возвращает список
- [ ] GET /api/tools/calculate — возвращает детали
- [ ] POST /api/tools/calculate/enable — включает
- [ ] POST /api/tools/calculate/disable — выключает
- [ ] PUT /api/tools/{name}/settings — сохраняет
- [ ] GET /api/plugins — возвращает список плагинов
- [ ] POST /api/plugins/reload — перезагружает

**Проверка персистентности:**
- [ ] Включить инструмент → перезапустить → проверить что включён
- [ ] Сохранить настройки → перезапустить → проверить что сохранены

**Проверка шифрования:**
- [ ] Посмотреть в БД — settings_json зашифрован
- [ ] API возвращает расшифрованные (с маской для паролей)

### Критерий готовности
- [ ] Все unit-тесты проходят
- [ ] Ручное тестирование пройдено
- [ ] Нет регрессий

---

## Последовательность работ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 1: Storage                                                            │
│                                                                             │
│  Утро:                                                                      │
│  ├── 3.1 Модель ToolSettingsModel в db.py                                  │
│  └── Тест создания таблицы                                                 │
│                                                                             │
│  После обеда:                                                               │
│  ├── 3.2 Tools Repository                                                  │
│  └── Тесты CRUD и шифрования                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 2: Settings Manager + API (часть 1)                                   │
│                                                                             │
│  Утро:                                                                      │
│  ├── 3.3 Расширение settings_manager.py                                    │
│  └── Тесты settings_manager                                                │
│                                                                             │
│  После обеда:                                                               │
│  ├── 3.4 Tools Router (GET /api/tools, GET /api/tools/{name})              │
│  └── Тесты                                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 3: API (часть 2) + Интеграция                                        │
│                                                                             │
│  Утро:                                                                      │
│  ├── 3.4 Tools Router (enable, disable, settings, test)                    │
│  └── Тесты                                                                 │
│                                                                             │
│  После обеда:                                                               │
│  ├── 3.5 Plugins Router                                                    │
│  ├── 3.6 Интеграция в app.py                                               │
│  └── Тесты                                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 4: Тестирование                                                      │
│                                                                             │
│  ├── 3.7 Ручное тестирование по чеклисту                                   │
│  ├── Исправление багов                                                     │
│  └── Документация API (Swagger)                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  РЕЗУЛЬТАТ ФАЗЫ 3                                                          │
│                                                                             │
│  ✅ Настройки плагинов сохраняются в БД                                    │
│  ✅ Секреты зашифрованы                                                     │
│  ✅ API для управления инструментами работает                              │
│  ✅ API для управления плагинами работает                                  │
│  ✅ Персистентность: настройки переживают перезапуск                       │
│  ✅ Готов бэкенд для Фазы 4 (Админка Инструменты)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Summary

### Tools Router (/api/tools)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/tools | Список инструментов |
| GET | /api/tools/{name} | Детали инструмента |
| POST | /api/tools/{name}/enable | Включить |
| POST | /api/tools/{name}/disable | Выключить |
| GET | /api/tools/{name}/settings | Получить настройки |
| PUT | /api/tools/{name}/settings | Сохранить настройки |
| POST | /api/tools/{name}/test | Тест подключения |

### Plugins Router (/api/plugins)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/plugins | Список плагинов |
| POST | /api/plugins/reload | Перезагрузить все |
| POST | /api/plugins/{id}/reload | Перезагрузить один |

---

## Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Миграция БД сломает данные | Низкая | Высокое | Новая таблица, не трогаем старые |
| Шифрование несовместимо | Низкая | Среднее | Используем существующий encryption.py |
| Гонки при параллельных запросах | Средняя | Среднее | Транзакции SQLAlchemy |

---

## Definition of Done для Фазы 3

- [ ] Все задачи 3.1-3.7 выполнены
- [ ] Модель ToolSettingsModel создана
- [ ] Repository работает
- [ ] Settings Manager интегрирован с БД
- [ ] Tools Router реализован
- [ ] Plugins Router реализован
- [ ] Интеграция в app.py завершена
- [ ] Все тесты проходят
- [ ] Ручное тестирование пройдено
- [ ] Swagger документация актуальна
- [ ] Нет регрессий

---

## Что НЕ входит в Фазу 3

- ❌ UI админки (Фаза 4)
- ❌ Бизнес-плагины (Фаза 6)

---

## Версионирование документа

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0 | 2026-02-06 | Первая версия плана Фазы 3 |
