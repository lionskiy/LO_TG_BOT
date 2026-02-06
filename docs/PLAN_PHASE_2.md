# PHASE 2: Plugin System

> **Детальная постановка задач для Фазы 2**  
> Система плагинов: Registry, Loader, Executor, Builtin-плагины

**Версия:** 1.0  
**Дата:** 2026-02-06  
**Ориентировочный срок:** 5-7 дней  
**Предусловие:** Фаза 1 завершена (tool-calling работает)

---

## Связанные документы

| Документ | Описание | Статус |
|----------|----------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Целевая архитектура системы | ✅ Актуален (не завершено) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Декомпозиция всех задач | ✅ Актуален (не завершено) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Детальный план Фазы 0-1 | ✅ Актуален (не завершено) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Детальный план Фазы 2 (этот документ) | ✅ Актуален (не завершено) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Детальный план Фазы 3 (следующая) | ✅ Актуален (не завершено) |

### Существующая документация проекта

| Документ | Описание |
|----------|----------|
| [CURRENT_IMPLEMENTATION.md](CURRENT_IMPLEMENTATION.md) | Текущая реализация |
| [APP_DESCRIPTION_AND_API.md](APP_DESCRIPTION_AND_API.md) | Описание приложения и API |

---

## Навигация по фазам

| Фаза | Документ | Описание | Статус |
|------|----------|----------|--------|
| 0-1 | [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Стабилизация + Tool-Calling | ✅ Актуален (не завершено) |
| 2 | **[PLAN_PHASE_2.md](PLAN_PHASE_2.md)** | Plugin System | ✅ Актуален (не завершено) |
| 3 | [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Storage + API | ✅ Актуален (не завершено) |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Админка Инструменты | ✅ Актуален (не завершено) |
| 5 | [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Админка Администраторы | ✅ Актуален (не завершено) |
| 6 | [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Worklog Checker | ✅ Актуален (не завершено) |

---

## Общая цель Фазы 2

**Было (после Фазы 1):** Tool-calling работает, но инструменты захардкожены в коде `bot/tool_calling.py`.

**Стало:** Инструменты загружаются из папки `plugins/` как отдельные модули. Добавление нового инструмента = добавление файлов в папку (без изменения кода ядра).

**Важно:** 
- Захардкоженные инструменты из Фазы 1 переносятся в плагины
- Tool-calling продолжает работать без изменений для пользователя
- Настройки плагинов пока НЕ сохраняются в БД (это Фаза 3)

---

## Архитектура Фазы 2

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  telegram_bot.py                                                            │
│  │                                                                          │
│  └── handle_message() → get_reply_with_tools()                              │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │  tool_calling.py                                                        │
│  │                                                                         │
│  │  get_reply_with_tools(messages)                                         │
│  │  │                                                                      │
│  │  ├── tools = registry.get_tools_for_llm()    ← ИЗМЕНЕНИЕ               │
│  │  ├── response = llm.get_reply(messages, tools)                          │
│  │  ├── if tool_calls:                                                     │
│  │  │   └── result = executor.execute(tool_call)  ← ИЗМЕНЕНИЕ             │
│  │  └── return final_response                                              │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
│                              │
│              ┌───────────────┼───────────────┐
│              ▼               ▼               ▼
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  │   Registry    │  │   Executor    │  │    Loader     │
│  │               │  │               │  │               │
│  │ • tools dict  │  │ • execute()   │  │ • scan()      │
│  │ • get_tools() │  │ • timeout     │  │ • load()      │
│  │ • get_tool()  │  │ • errors      │  │ • reload()    │
│  └───────────────┘  └───────────────┘  └───────────────┘
│         ▲                                     │
│         │                                     │
│         └─────────────────────────────────────┘
│                       регистрация
│                              │
│                              ▼
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │  plugins/                                                               │
│  │  │                                                                      │
│  │  ├── builtin/                                                           │
│  │  │   ├── calculator/                                                    │
│  │  │   │   ├── plugin.yaml                                                │
│  │  │   │   └── handlers.py                                                │
│  │  │   │                                                                  │
│  │  │   └── datetime_tools/                                                │
│  │  │       ├── plugin.yaml                                                │
│  │  │       └── handlers.py                                                │
│  │  │                                                                      │
│  │  └── (будущие плагины...)                                               │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Структура папки tools/

```
LO_TG_BOT/
├── tools/                      # Модуль системы плагинов
│   ├── __init__.py             # Экспорт публичного API
│   ├── models.py               # Pydantic модели (ToolDefinition, PluginManifest, etc.)
│   ├── registry.py             # Tool Registry
│   ├── loader.py               # Plugin Loader
│   ├── executor.py             # Tool Executor
│   └── base.py                 # Утилиты для плагинов
│
└── plugins/                    # Папка с плагинами
    ├── __init__.py             # Пустой
    └── builtin/                # Встроенные плагины
        ├── calculator/
        │   ├── plugin.yaml
        │   └── handlers.py
        └── datetime_tools/
            ├── plugin.yaml
            └── handlers.py
```

---

# Задачи Фазы 2

---

## Задача 2.1: Модели данных (tools/models.py)

### Описание
Создать Pydantic-модели для описания плагинов, инструментов и связанных структур.

### Файл: tools/models.py

### Модели

#### ToolParameter
```python
class ToolParameter(BaseModel):
    """Описание параметра инструмента"""
    name: str
    type: str                    # string, number, boolean, array, object
    description: str
    required: bool = False
    default: Any = None
    enum: List[Any] | None = None  # Для ограниченного набора значений
```

#### ToolDefinition
```python
class ToolDefinition(BaseModel):
    """Полное описание инструмента"""
    name: str                    # Уникальное имя (например: "calculate")
    description: str             # Описание для LLM (английский)
    plugin_id: str               # ID плагина-владельца
    handler: Callable | None = None  # Функция-обработчик (не сериализуется)
    parameters: Dict[str, Any]   # JSON Schema параметров
    timeout: int = 30            # Таймаут выполнения в секундах
    enabled: bool = True         # Включён ли инструмент
    
    class Config:
        arbitrary_types_allowed = True  # Для Callable
```

#### PluginSettingDefinition
```python
class PluginSettingDefinition(BaseModel):
    """Описание настройки плагина"""
    key: str                     # Ключ настройки
    label: str                   # Название для UI
    type: str                    # string, password, number, boolean, select
    description: str | None = None
    required: bool = False
    default: Any = None
    options: List[Any] | None = None  # Для select
```

#### PluginManifest
```python
class PluginManifest(BaseModel):
    """Манифест плагина (из plugin.yaml)"""
    id: str                      # Уникальный ID плагина
    name: str                    # Название для UI
    version: str                 # Версия (semver)
    description: str | None = None
    enabled: bool = True         # Включён по умолчанию
    tools: List[ToolManifestItem]  # Список инструментов
    settings: List[PluginSettingDefinition] = []  # Настройки плагина
```

#### ToolManifestItem
```python
class ToolManifestItem(BaseModel):
    """Описание инструмента в манифесте"""
    name: str
    description: str
    handler: str                 # Имя функции в handlers.py
    timeout: int = 30
    parameters: Dict[str, Any]   # JSON Schema
```

#### ToolCall и ToolResult (перенос из Фазы 1)
```python
@dataclass
class ToolCall:
    """Вызов инструмента от LLM"""
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass  
class ToolResult:
    """Результат выполнения инструмента"""
    tool_call_id: str
    content: str
    success: bool = True
    error: str | None = None
```

### Критерий готовности
- [ ] Все модели созданы в tools/models.py
- [ ] Модели валидируют данные (Pydantic)
- [ ] ToolCall/ToolResult перенесены из bot/llm.py
- [ ] Тесты на валидацию моделей

---

## Задача 2.2: Tool Registry (tools/registry.py)

### Описание
Централизованное хранилище всех зарегистрированных инструментов. Предоставляет API для регистрации, получения и управления инструментами.

### Файл: tools/registry.py

### Класс ToolRegistry

```python
class ToolRegistry:
    """
    Реестр инструментов.
    Singleton — один экземпляр на всё приложение.
    """
```

### Внутреннее хранилище
```python
_tools: Dict[str, ToolDefinition] = {}      # tool_name → ToolDefinition
_plugins: Dict[str, PluginManifest] = {}    # plugin_id → PluginManifest
```

### Публичные методы

#### Регистрация
```python
def register_tool(self, tool: ToolDefinition) -> None:
    """
    Регистрирует инструмент в реестре.
    
    Args:
        tool: Определение инструмента
        
    Raises:
        ValueError: Если инструмент с таким именем уже существует
    """
    
def register_plugin(self, manifest: PluginManifest) -> None:
    """
    Регистрирует плагин (без инструментов).
    Инструменты регистрируются отдельно через register_tool().
    """

def unregister_plugin(self, plugin_id: str) -> None:
    """
    Удаляет плагин и все его инструменты из реестра.
    Используется при hot-reload.
    """
```

#### Получение инструментов
```python
def get_tool(self, name: str) -> ToolDefinition | None:
    """Получить инструмент по имени"""

def get_all_tools(self) -> List[ToolDefinition]:
    """Получить все инструменты (включая отключённые)"""

def get_enabled_tools(self) -> List[ToolDefinition]:
    """Получить только включённые инструменты"""

def get_tools_by_plugin(self, plugin_id: str) -> List[ToolDefinition]:
    """Получить инструменты конкретного плагина"""
```

#### Формирование для LLM
```python
def get_tools_for_llm(self) -> List[Dict[str, Any]]:
    """
    Возвращает список инструментов в формате OpenAI для передачи в LLM.
    Только включённые инструменты.
    
    Returns:
        [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "...",
                    "parameters": {...}
                }
            },
            ...
        ]
    """
```

#### Управление состоянием
```python
def enable_tool(self, name: str) -> bool:
    """Включить инструмент. Возвращает успех."""

def disable_tool(self, name: str) -> bool:
    """Выключить инструмент. Возвращает успех."""

def is_tool_enabled(self, name: str) -> bool:
    """Проверить включён ли инструмент"""
```

#### Служебные
```python
def clear(self) -> None:
    """Очистить реестр (для тестов и reload)"""

def get_stats(self) -> Dict[str, Any]:
    """
    Статистика реестра.
    Returns: {
        "total_plugins": 2,
        "total_tools": 3,
        "enabled_tools": 2
    }
    """
```

### Singleton паттерн
```python
# Глобальный экземпляр
_registry: ToolRegistry | None = None

def get_registry() -> ToolRegistry:
    """Получить глобальный экземпляр реестра"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
```

### Критерий готовности
- [ ] Класс ToolRegistry реализован
- [ ] Все публичные методы работают
- [ ] get_tools_for_llm() возвращает корректный формат
- [ ] Singleton работает
- [ ] Тесты на все методы

---

## Задача 2.3: Plugin Loader (tools/loader.py)

### Описание
Сканирует папку `plugins/`, читает манифесты, загружает код обработчиков и регистрирует инструменты в Registry.

### Файл: tools/loader.py

### Основные функции

#### load_all_plugins
```python
async def load_all_plugins(
    plugins_dir: str = "plugins",
    registry: ToolRegistry | None = None
) -> LoadResult:
    """
    Загружает все плагины из указанной директории.
    
    Args:
        plugins_dir: Путь к папке с плагинами
        registry: Реестр (если None — используется глобальный)
        
    Returns:
        LoadResult с информацией о загруженных плагинах и ошибках
    """
```

#### load_plugin
```python
async def load_plugin(
    plugin_path: str,
    registry: ToolRegistry | None = None
) -> PluginManifest | None:
    """
    Загружает один плагин из указанной папки.
    
    Args:
        plugin_path: Путь к папке плагина (содержит plugin.yaml)
        registry: Реестр для регистрации
        
    Returns:
        PluginManifest если успешно, None если ошибка
        
    Raises:
        PluginLoadError: При критических ошибках загрузки
    """
```

#### reload_plugin
```python
async def reload_plugin(
    plugin_id: str,
    plugins_dir: str = "plugins",
    registry: ToolRegistry | None = None
) -> bool:
    """
    Перезагружает плагин (unregister + load).
    
    Шаги:
    1. Найти папку плагина по ID
    2. Удалить из реестра (unregister_plugin)
    3. Перезагрузить модуль Python (importlib.reload)
    4. Загрузить заново (load_plugin)
    
    Returns:
        True если успешно
    """
```

#### reload_all_plugins
```python
async def reload_all_plugins(
    plugins_dir: str = "plugins",
    registry: ToolRegistry | None = None
) -> LoadResult:
    """
    Перезагружает все плагины.
    
    Шаги:
    1. Очистить реестр
    2. Загрузить все плагины заново
    """
```

### Структура LoadResult
```python
@dataclass
class LoadResult:
    """Результат загрузки плагинов"""
    loaded: List[str]            # ID успешно загруженных плагинов
    failed: List[LoadError]      # Ошибки загрузки
    total_tools: int             # Всего инструментов загружено

@dataclass
class LoadError:
    """Ошибка загрузки плагина"""
    plugin_id: str | None        # ID плагина (если известен)
    plugin_path: str             # Путь к папке
    error: str                   # Сообщение об ошибке
    exception: Exception | None  # Исключение (для логов)
```

### Алгоритм загрузки плагина

```
load_plugin(plugin_path):
│
├── 1. ЧТЕНИЕ МАНИФЕСТА
│   ├── Проверить существование plugin.yaml
│   ├── Прочитать YAML
│   ├── Валидировать через PluginManifest (Pydantic)
│   └── При ошибке → вернуть None, залогировать
│
├── 2. ЗАГРУЗКА КОДА
│   ├── Проверить существование handlers.py
│   ├── Загрузить модуль через importlib.util
│   │   ├── spec = importlib.util.spec_from_file_location(...)
│   │   ├── module = importlib.util.module_from_spec(spec)
│   │   └── spec.loader.exec_module(module)
│   └── При ошибке → вернуть None, залогировать
│
├── 3. СВЯЗЫВАНИЕ HANDLERS
│   ├── Для каждого tool в manifest.tools:
│   │   ├── Найти функцию handler в module
│   │   ├── Проверить что это callable
│   │   ├── Проверить что async (опционально)
│   │   └── При ошибке → пропустить tool, залогировать
│   │
│   └── Создать ToolDefinition с привязанным handler
│
├── 4. РЕГИСТРАЦИЯ
│   ├── registry.register_plugin(manifest)
│   └── Для каждого tool:
│       └── registry.register_tool(tool_definition)
│
└── 5. РЕЗУЛЬТАТ
    ├── Залогировать успех
    └── Вернуть manifest
```

### Обработка ошибок

| Ситуация | Поведение |
|----------|-----------|
| plugin.yaml не найден | Пропустить папку, warning в лог |
| plugin.yaml невалидный | Пропустить плагин, error в лог |
| handlers.py не найден | Пропустить плагин, error в лог |
| Ошибка импорта handlers.py | Пропустить плагин, error в лог |
| Handler функция не найдена | Пропустить tool, warning в лог |
| Handler не callable | Пропустить tool, warning в лог |

### Фильтрация при сканировании
```python
IGNORE_DIRS = {'__pycache__', '.git', '.idea', 'node_modules', '.venv'}

def _should_scan_dir(dirname: str) -> bool:
    """Проверяет нужно ли сканировать папку"""
    return (
        not dirname.startswith('.') and
        not dirname.startswith('_') and
        dirname not in IGNORE_DIRS
    )
```

### Критерий готовности
- [ ] load_all_plugins() загружает плагины из папки
- [ ] load_plugin() загружает один плагин
- [ ] reload_plugin() перезагружает плагин
- [ ] Манифест валидируется через Pydantic
- [ ] Handlers загружаются через importlib
- [ ] Ошибки не ломают загрузку других плагинов
- [ ] Логирование всех этапов
- [ ] Тесты на успешную загрузку
- [ ] Тесты на ошибки (битый YAML, отсутствующий handler)

---

## Задача 2.4: Tool Executor (tools/executor.py)

### Описание
Выполняет инструменты: получает ToolCall, находит handler в Registry, вызывает с аргументами, возвращает результат.

### Файл: tools/executor.py

### Основная функция

```python
async def execute_tool(
    tool_call: ToolCall,
    registry: ToolRegistry | None = None,
    timeout: int | None = None
) -> ToolResult:
    """
    Выполняет вызов инструмента.
    
    Args:
        tool_call: Вызов от LLM (name, arguments)
        registry: Реестр инструментов
        timeout: Таймаут (если None — из ToolDefinition)
        
    Returns:
        ToolResult с результатом или ошибкой
    """
```

### Алгоритм выполнения

```
execute_tool(tool_call):
│
├── 1. ПОИСК ИНСТРУМЕНТА
│   ├── tool = registry.get_tool(tool_call.name)
│   ├── Если не найден → вернуть ToolResult с ошибкой
│   └── Если отключён → вернуть ToolResult с ошибкой
│
├── 2. ПОДГОТОВКА
│   ├── handler = tool.handler
│   ├── arguments = tool_call.arguments
│   └── effective_timeout = timeout or tool.timeout
│
├── 3. ВЫПОЛНЕНИЕ
│   ├── start_time = time.time()
│   │
│   ├── try:
│   │   ├── result = await asyncio.wait_for(
│   │   │       handler(**arguments),
│   │   │       timeout=effective_timeout
│   │   │   )
│   │   └── duration = time.time() - start_time
│   │
│   ├── except asyncio.TimeoutError:
│   │   └── вернуть ToolResult(success=False, error="Timeout")
│   │
│   ├── except TypeError as e:  # Неверные аргументы
│   │   └── вернуть ToolResult(success=False, error=str(e))
│   │
│   └── except Exception as e:
│       ├── Залогировать полный traceback
│       └── вернуть ToolResult(success=False, error=str(e))
│
├── 4. ФОРМИРОВАНИЕ РЕЗУЛЬТАТА
│   ├── Если result — dict → сериализовать в JSON
│   ├── Если result — str → использовать как есть
│   └── Иначе → str(result)
│
├── 5. ЛОГИРОВАНИЕ
│   └── Лог: tool_name, duration, success, error (если есть)
│
└── 6. ВОЗВРАТ
    └── ToolResult(tool_call_id, content, success=True)
```

### Вспомогательные функции

```python
async def execute_tools(
    tool_calls: List[ToolCall],
    registry: ToolRegistry | None = None,
    parallel: bool = False
) -> List[ToolResult]:
    """
    Выполняет несколько инструментов.
    
    Args:
        tool_calls: Список вызовов
        parallel: Выполнять параллельно (asyncio.gather)
                  или последовательно
                  
    Returns:
        Список результатов в том же порядке
    """
```

### Формат ошибок для LLM

При ошибке выполнения в `ToolResult.content` возвращается понятное сообщение:

```python
ERROR_MESSAGES = {
    "not_found": "Tool '{name}' not found",
    "disabled": "Tool '{name}' is currently disabled",
    "timeout": "Tool '{name}' execution timed out after {timeout}s",
    "invalid_args": "Invalid arguments for tool '{name}': {error}",
    "execution": "Tool '{name}' failed: {error}"
}
```

### Критерий готовности
- [ ] execute_tool() выполняет инструмент
- [ ] Таймаут работает (asyncio.wait_for)
- [ ] Ошибки обрабатываются gracefully
- [ ] Результат сериализуется корректно
- [ ] Логирование вызовов
- [ ] Тесты на успешное выполнение
- [ ] Тесты на таймаут
- [ ] Тесты на ошибки

---

## Задача 2.5: Plugin Base (tools/base.py)

### Описание
Утилиты для использования в плагинах: доступ к настройкам, HTTP-клиент, логирование.

### Файл: tools/base.py

### Функции

#### Доступ к настройкам
```python
def get_plugin_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    """
    Получить значение настройки плагина.
    
    В Фазе 2: возвращает default (настройки в БД появятся в Фазе 3)
    В Фазе 3+: читает из БД
    
    Args:
        plugin_id: ID плагина
        key: Ключ настройки
        default: Значение по умолчанию
        
    Returns:
        Значение настройки или default
    """

def require_plugin_setting(plugin_id: str, key: str) -> Any:
    """
    Получить обязательную настройку.
    
    Raises:
        PluginConfigError: Если настройка не задана
    """
```

#### HTTP клиент
```python
def get_http_client(
    timeout: float = 30.0,
    follow_redirects: bool = True
) -> httpx.AsyncClient:
    """
    Получить настроенный HTTP клиент.
    
    Returns:
        httpx.AsyncClient с преднастроенными таймаутами
    """
```

#### Логирование
```python
def get_plugin_logger(plugin_id: str) -> logging.Logger:
    """
    Получить логгер для плагина.
    
    Логгер имеет префикс [plugin_id] в сообщениях.
    
    Returns:
        logging.Logger
    """
```

#### Контекст выполнения (для будущего)
```python
@dataclass
class ToolContext:
    """Контекст выполнения инструмента"""
    user_id: str | None = None      # Telegram user ID
    chat_id: str | None = None      # Telegram chat ID
    plugin_id: str | None = None    # ID плагина
    
# Глобальный контекст (thread-local или contextvars)
_current_context: ToolContext | None = None

def get_current_context() -> ToolContext | None:
    """Получить текущий контекст выполнения"""
    return _current_context
```

### Критерий готовности
- [ ] get_plugin_setting() работает (возвращает default в Фазе 2)
- [ ] get_http_client() возвращает настроенный клиент
- [ ] get_plugin_logger() возвращает логгер с префиксом
- [ ] Тесты на утилиты

---

## Задача 2.6: Публичный API модуля (tools/__init__.py)

### Описание
Экспортировать публичные функции и классы для использования в других модулях.

### Файл: tools/__init__.py

```python
"""
Tools — система плагинов для LO_TG_BOT.

Использование:
    from tools import get_registry, load_all_plugins, execute_tool
    
    # Загрузка плагинов при старте
    await load_all_plugins()
    
    # Получение инструментов для LLM
    tools = get_registry().get_tools_for_llm()
    
    # Выполнение инструмента
    result = await execute_tool(tool_call)
"""

from tools.models import (
    ToolDefinition,
    ToolCall,
    ToolResult,
    PluginManifest,
)

from tools.registry import (
    ToolRegistry,
    get_registry,
)

from tools.loader import (
    load_all_plugins,
    load_plugin,
    reload_plugin,
    reload_all_plugins,
    LoadResult,
)

from tools.executor import (
    execute_tool,
    execute_tools,
)

from tools.base import (
    get_plugin_setting,
    require_plugin_setting,
    get_http_client,
    get_plugin_logger,
)

__all__ = [
    # Models
    "ToolDefinition",
    "ToolCall", 
    "ToolResult",
    "PluginManifest",
    
    # Registry
    "ToolRegistry",
    "get_registry",
    
    # Loader
    "load_all_plugins",
    "load_plugin",
    "reload_plugin",
    "reload_all_plugins",
    "LoadResult",
    
    # Executor
    "execute_tool",
    "execute_tools",
    
    # Base
    "get_plugin_setting",
    "require_plugin_setting",
    "get_http_client",
    "get_plugin_logger",
]
```

### Критерий готовности
- [ ] Все публичные API экспортируются
- [ ] Импорт `from tools import ...` работает
- [ ] Docstring с примером использования

---

## Задача 2.7: Builtin-плагин Calculator

### Описание
Перенести калькулятор из захардкоженного кода в плагин.

### Структура
```
plugins/builtin/calculator/
├── plugin.yaml
└── handlers.py
```

### plugin.yaml
```yaml
id: calculator
name: "Calculator"
version: "1.0.0"
description: "Mathematical expression evaluator"
enabled: true

tools:
  - name: calculate
    description: "Evaluates a mathematical expression and returns the result. Supports: +, -, *, /, **, parentheses, sqrt, sin, cos, tan, log, abs, round, pi, e."
    handler: calculate
    timeout: 10
    parameters:
      type: object
      properties:
        expression:
          type: string
          description: "Mathematical expression to evaluate, e.g. '2 + 2 * 3' or 'sqrt(16) + pi'"
      required:
        - expression
```

### handlers.py
```python
"""Calculator plugin handlers."""

import math
import operator
from typing import Union

# Безопасные операции
SAFE_OPERATORS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '**': operator.pow,
    '%': operator.mod,
}

SAFE_FUNCTIONS = {
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log,
    'log10': math.log10,
    'abs': abs,
    'round': round,
    'floor': math.floor,
    'ceil': math.ceil,
}

SAFE_CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
}


async def calculate(expression: str) -> str:
    """
    Вычисляет математическое выражение.
    
    Args:
        expression: Выражение для вычисления
        
    Returns:
        Строка с результатом или сообщением об ошибке
    """
    try:
        # Используем безопасный eval или библиотеку simpleeval
        result = _safe_eval(expression)
        
        # Форматирование результата
        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            return f"{result:.10g}"  # Убираем лишние нули
        return str(result)
        
    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: Cannot evaluate expression - {e}"


def _safe_eval(expression: str) -> Union[int, float]:
    """
    Безопасное вычисление выражения.
    
    Варианты реализации:
    1. simpleeval библиотека (рекомендуется)
    2. ast.literal_eval + ручной парсинг
    3. Собственный парсер
    """
    # TODO: Реализовать через simpleeval или ast
    pass
```

### Критерий готовности
- [ ] plugin.yaml создан и валиден
- [ ] handlers.py реализован
- [ ] Безопасное вычисление (нет code injection)
- [ ] Поддержка базовых операций: +, -, *, /, **
- [ ] Поддержка функций: sqrt, sin, cos, tan, log
- [ ] Поддержка констант: pi, e
- [ ] Корректная обработка ошибок
- [ ] Тесты

---

## Задача 2.8: Builtin-плагин DateTime

### Описание
Перенести datetime-инструменты из захардкоженного кода в плагин.

### Структура
```
plugins/builtin/datetime_tools/
├── plugin.yaml
└── handlers.py
```

### plugin.yaml
```yaml
id: datetime-tools
name: "Date & Time"
version: "1.0.0"
description: "Date and time utilities"
enabled: true

tools:
  - name: get_current_datetime
    description: "Returns current date and time with weekday name. Use this when user asks about current time or date."
    handler: get_current_datetime
    timeout: 5
    parameters:
      type: object
      properties:
        timezone:
          type: string
          description: "Timezone name (e.g. 'Europe/Moscow', 'UTC'). Default is server timezone."
      required: []

  - name: get_weekday
    description: "Returns the weekday name for a given date."
    handler: get_weekday
    timeout: 5
    parameters:
      type: object
      properties:
        date:
          type: string
          description: "Date in format YYYY-MM-DD, DD.MM.YYYY, or natural language like 'tomorrow', 'next monday'"
      required:
        - date

  - name: calculate_date_difference
    description: "Calculates the difference between two dates in days."
    handler: calculate_date_difference
    timeout: 5
    parameters:
      type: object
      properties:
        date1:
          type: string
          description: "First date"
        date2:
          type: string
          description: "Second date"
      required:
        - date1
        - date2
```

### handlers.py
```python
"""DateTime plugin handlers."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional


async def get_current_datetime(timezone: Optional[str] = None) -> str:
    """
    Возвращает текущую дату и время.
    
    Args:
        timezone: Часовой пояс (опционально)
        
    Returns:
        Строка вида "2024-01-15 14:30:00 (Monday)"
    """
    try:
        if timezone:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now()
        
        weekday = now.strftime("%A")
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        
        return f"{formatted} ({weekday})"
        
    except Exception as e:
        return f"Error: {e}"


async def get_weekday(date: str) -> str:
    """
    Возвращает день недели для указанной даты.
    
    Args:
        date: Дата в различных форматах
        
    Returns:
        Название дня недели
    """
    try:
        parsed = _parse_date(date)
        if parsed is None:
            return f"Error: Cannot parse date '{date}'"
        
        weekday = parsed.strftime("%A")
        formatted = parsed.strftime("%Y-%m-%d")
        
        return f"{formatted} is {weekday}"
        
    except Exception as e:
        return f"Error: {e}"


async def calculate_date_difference(date1: str, date2: str) -> str:
    """
    Вычисляет разницу между датами в днях.
    """
    try:
        d1 = _parse_date(date1)
        d2 = _parse_date(date2)
        
        if d1 is None:
            return f"Error: Cannot parse date '{date1}'"
        if d2 is None:
            return f"Error: Cannot parse date '{date2}'"
        
        diff = abs((d2 - d1).days)
        return f"{diff} days"
        
    except Exception as e:
        return f"Error: {e}"


def _parse_date(date_str: str) -> Optional[datetime]:
    """
    Парсит дату из различных форматов.
    
    Поддерживает:
    - YYYY-MM-DD
    - DD.MM.YYYY
    - DD/MM/YYYY
    - today, tomorrow, yesterday
    """
    date_str = date_str.strip().lower()
    
    # Специальные значения
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_str == 'today':
        return today
    elif date_str == 'tomorrow':
        return today + timedelta(days=1)
    elif date_str == 'yesterday':
        return today - timedelta(days=1)
    
    # Форматы дат
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None
```

### Критерий готовности
- [ ] plugin.yaml создан и валиден
- [ ] get_current_datetime работает
- [ ] get_weekday работает с разными форматами
- [ ] calculate_date_difference работает
- [ ] Поддержка timezone
- [ ] Поддержка special values (today, tomorrow)
- [ ] Тесты

---

## Задача 2.9: Интеграция с tool_calling.py

### Описание
Модифицировать `bot/tool_calling.py` для использования Registry и Executor вместо захардкоженных инструментов.

### Изменения в bot/tool_calling.py

**Было (Фаза 1):**
```python
# Захардкоженные инструменты
HARDCODED_TOOLS = [...]

async def get_reply_with_tools(messages):
    tools = HARDCODED_TOOLS
    ...
    # Выполнение через локальные функции
    result = await execute_hardcoded_tool(tool_call)
```

**Стало (Фаза 2):**
```python
from tools import get_registry, execute_tool, load_all_plugins

# При первом вызове загружаем плагины
_plugins_loaded = False

async def _ensure_plugins_loaded():
    global _plugins_loaded
    if not _plugins_loaded:
        await load_all_plugins()
        _plugins_loaded = True


async def get_reply_with_tools(messages):
    await _ensure_plugins_loaded()
    
    registry = get_registry()
    tools = registry.get_tools_for_llm()
    
    if not tools:
        # Нет инструментов — обычный ответ
        return await get_reply(messages)
    
    ...
    
    # Выполнение через Executor
    for tool_call in tool_calls:
        result = await execute_tool(tool_call)
        ...
```

### Удаление захардкоженного кода
- Удалить `HARDCODED_TOOLS`
- Удалить локальные функции `get_current_datetime()`, `calculate()`
- Удалить локальную функцию `execute_hardcoded_tool()`

### Критерий готовности
- [ ] tool_calling.py использует Registry
- [ ] tool_calling.py использует Executor
- [ ] Захардкоженный код удалён
- [ ] Плагины загружаются при первом вызове
- [ ] Тесты проходят
- [ ] Ручное тестирование: "Сколько времени?" и "Посчитай 2+2"

---

## Задача 2.10: Тестирование Фазы 2

### Unit-тесты

#### tests/test_tools_models.py
```
test_tool_definition_validation
test_plugin_manifest_validation
test_tool_call_creation
test_tool_result_creation
```

#### tests/test_tools_registry.py
```
test_register_tool
test_register_duplicate_tool_raises
test_get_tool
test_get_tool_not_found
test_get_enabled_tools
test_get_tools_for_llm_format
test_enable_disable_tool
test_unregister_plugin
test_clear_registry
test_singleton_pattern
```

#### tests/test_tools_loader.py
```
test_load_all_plugins
test_load_plugin_success
test_load_plugin_missing_yaml
test_load_plugin_invalid_yaml
test_load_plugin_missing_handler
test_reload_plugin
test_reload_all_plugins
test_ignore_pycache_dirs
```

#### tests/test_tools_executor.py
```
test_execute_tool_success
test_execute_tool_not_found
test_execute_tool_disabled
test_execute_tool_timeout
test_execute_tool_exception
test_execute_tool_invalid_args
test_execute_tools_parallel
test_execute_tools_sequential
```

#### tests/test_builtin_plugins.py
```
# Calculator
test_calculate_basic_operations
test_calculate_functions
test_calculate_constants
test_calculate_division_by_zero
test_calculate_invalid_expression
test_calculate_safe_from_injection

# DateTime
test_get_current_datetime
test_get_current_datetime_with_timezone
test_get_weekday_iso_format
test_get_weekday_dot_format
test_get_weekday_special_values
test_calculate_date_difference
```

### Integration тесты

```
test_full_flow_calculator_through_llm
test_full_flow_datetime_through_llm
test_plugins_reload_updates_registry
```

### Ручное тестирование (чеклист)

**Подготовка:**
- [ ] Плагины в папке plugins/builtin/
- [ ] Бот запущен
- [ ] LLM настроен

**Calculator:**
- [ ] "Сколько будет 2+2?" → "4"
- [ ] "Посчитай 15% от 200" → "30"
- [ ] "Квадратный корень из 144" → "12"
- [ ] "sin(0) + cos(0)" → "1"
- [ ] "Раздели 10 на 0" → сообщение об ошибке

**DateTime:**
- [ ] "Сколько сейчас времени?" → текущее время
- [ ] "Какой сегодня день недели?" → правильный день
- [ ] "Какой день недели будет 01.01.2025?" → среда
- [ ] "Сколько дней до нового года?" → правильное число

**Обычные вопросы (без tools):**
- [ ] "Привет!" → обычный ответ
- [ ] "Расскажи анекдот" → обычный ответ

### Критерий готовности
- [ ] Все unit-тесты проходят
- [ ] Integration тесты проходят
- [ ] Ручное тестирование пройдено
- [ ] Нет регрессий

---

## Последовательность работ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 1: Модели и Registry                                                  │
│                                                                             │
│  Утро:                                                                      │
│  ├── 2.1 Создать tools/models.py                                           │
│  └── Тесты моделей                                                         │
│                                                                             │
│  После обеда:                                                               │
│  ├── 2.2 Создать tools/registry.py                                         │
│  └── Тесты registry                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 2: Loader                                                             │
│                                                                             │
│  ├── 2.3 Создать tools/loader.py                                           │
│  ├── Сканирование папок                                                    │
│  ├── Парсинг YAML                                                          │
│  ├── Загрузка handlers через importlib                                     │
│  └── Тесты loader                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 3: Executor и Base                                                    │
│                                                                             │
│  Утро:                                                                      │
│  ├── 2.4 Создать tools/executor.py                                         │
│  └── Тесты executor                                                        │
│                                                                             │
│  После обеда:                                                               │
│  ├── 2.5 Создать tools/base.py                                             │
│  ├── 2.6 Создать tools/__init__.py                                         │
│  └── Тесты base                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 4: Builtin-плагины                                                    │
│                                                                             │
│  Утро:                                                                      │
│  ├── 2.7 Создать plugins/builtin/calculator/                               │
│  └── Тесты calculator                                                      │
│                                                                             │
│  После обеда:                                                               │
│  ├── 2.8 Создать plugins/builtin/datetime_tools/                           │
│  └── Тесты datetime                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 5: Интеграция и тестирование                                         │
│                                                                             │
│  Утро:                                                                      │
│  ├── 2.9 Интеграция с tool_calling.py                                      │
│  └── Удаление захардкоженного кода                                         │
│                                                                             │
│  После обеда:                                                               │
│  ├── 2.10 Integration тесты                                                │
│  ├── Ручное тестирование                                                   │
│  └── Исправление багов                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  РЕЗУЛЬТАТ ФАЗЫ 2                                                          │
│                                                                             │
│  ✅ Plugin System работает                                                  │
│  ✅ Плагины загружаются из папки plugins/                                  │
│  ✅ Calculator и DateTime — полноценные плагины                            │
│  ✅ Добавление плагина = добавление файлов                                 │
│  ✅ Hot-reload плагинов (программно)                                       │
│  ✅ Готов фундамент для Фазы 3 (Storage + API)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Зависимости от внешних библиотек

### Новые зависимости (добавить в requirements.txt)

```
PyYAML>=6.0           # Парсинг plugin.yaml
simpleeval>=0.9.13    # Безопасное вычисление выражений (для calculator)
```

### Существующие (уже используются)
```
pydantic              # Валидация моделей
httpx                 # HTTP клиент (в base.py)
```

---

## Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| importlib не загружает модуль | Средняя | Высокое | Детальное логирование, тесты |
| Циклические импорты | Средняя | Среднее | Ленивые импорты, архитектура |
| YAML-парсинг падает | Низкая | Среднее | Pydantic валидация, try-except |
| simpleeval небезопасен | Низкая | Высокое | Ограничить функции, тесты на injection |
| Плагин ломает весь бот | Средняя | Высокое | Изоляция ошибок, fallback |

---

## Definition of Done для Фазы 2

- [ ] Все задачи 2.1-2.10 выполнены
- [ ] Модуль tools/ создан и работает
- [ ] Builtin-плагины работают
- [ ] Захардкоженные инструменты удалены
- [ ] Все тесты проходят
- [ ] Ручное тестирование пройдено
- [ ] Нет регрессий
- [ ] Код отревьюен
- [ ] Документация обновлена

---

## Что НЕ входит в Фазу 2

- ❌ Сохранение настроек плагинов в БД (Фаза 3)
- ❌ API для управления плагинами (Фаза 3)
- ❌ UI для управления плагинами (Фаза 4)
- ❌ Бизнес-плагины (Worklog Checker и т.д.) (Фаза 6)

---

## Версионирование документа

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0 | 2026-02-06 | Первая версия плана Фазы 2 |
