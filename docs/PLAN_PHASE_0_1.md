# PHASE 0-1: Стабилизация и Tool-Calling

> **Детальная постановка задач для Фаз 0 и 1**  
> Подготовка базы и внедрение tool-calling в LLM Engine

**Версия:** 1.1  
**Дата:** 2026-02-06  
**Ориентировочный срок:** 5-7 дней

---

## Связанные документы

| Документ | Описание | Статус |
|----------|----------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Целевая архитектура системы | ✅ Актуален (не завершено) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Декомпозиция всех задач | ✅ Актуален (не завершено) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Детальный план Фазы 0-1 (этот документ) | ✅ Актуален (не завершено) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Детальный план Фазы 2 (следующая фаза) | ✅ Актуален (не завершено) |

### Существующая документация проекта

| Документ | Описание |
|----------|----------|
| [CURRENT_IMPLEMENTATION.md](CURRENT_IMPLEMENTATION.md) | Текущая реализация (до изменений) |
| [APP_DESCRIPTION_AND_API.md](APP_DESCRIPTION_AND_API.md) | Описание приложения и API |

---

## Навигация по фазам

| Фаза | Документ | Описание | Статус |
|------|----------|----------|--------|
| 0-1 | **[PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md)** | Стабилизация + Tool-Calling | ✅ Актуален (не завершено) |
| 2 | [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Plugin System | ✅ Актуален (не завершено) |
| 3 | [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Storage + API | ✅ Актуален (не завершено) |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Админка Инструменты | ✅ Актуален (не завершено) |
| 5 | [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Админка Администраторы | ✅ Актуален (не завершено) |
| 6 | [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Worklog Checker | ✅ Актуален (не завершено) |

---

## Общая цель фаз 0-1

**Было:** Бот получает сообщение → отправляет в LLM → возвращает текстовый ответ.

**Стало:** Бот получает сообщение → отправляет в LLM с описанием tools → LLM может вызвать инструмент → результат инструмента возвращается в LLM → финальный ответ пользователю.

**Важно:** Текущая функциональность должна работать без изменений. Tool-calling — дополнение, не замена.

---

# ФАЗА 0: Стабилизация

**Цель:** Зафиксировать рабочее состояние, убедиться в наличии тестов, подготовить ветку для работ.

**Срок:** 1-2 дня

---

## Задача 0.1: Ревью текущего состояния

### Описание
Проверить что текущая реализация работает корректно, все тесты проходят, документация актуальна.

### Шаги
1. Запустить все существующие тесты: `pytest tests/`
2. Проверить что бот запускается в обоих режимах:
   - `python main.py` (настройки из .env)
   - `uvicorn api.app:app` (настройки из БД)
3. Проверить работу админки:
   - Настройки Telegram (сохранение, проверка, активация)
   - Настройки LLM (сохранение, проверка, активация)
   - Hot-swap работает
4. Проверить что бот отвечает на сообщения через настроенный LLM

### Критерий готовности
- [ ] Все тесты проходят (`pytest tests/` — green)
- [ ] Бот работает в режиме main.py
- [ ] Бот работает в режиме uvicorn + подпроцесс
- [ ] Админка функциональна
- [ ] Документация соответствует реальности

---

## Задача 0.2: Дополнение тестов (если необходимо)

### Описание
Добавить недостающие тесты для критичных путей, которые будут затронуты в Фазе 1.

### Что должно быть покрыто тестами
1. **bot/llm.py — get_reply()**
   - Тест: успешный ответ от LLM
   - Тест: обработка ошибки LLM (timeout, API error)
   - Тест: использование настроек из БД (приоритет над .env)

2. **bot/telegram_bot.py — обработка сообщений**
   - Тест: история диалога сохраняется
   - Тест: ограничение истории (20 пар)

3. **api/app.py — startup/shutdown**
   - Тест: приложение стартует без ошибок
   - Тест: бот-подпроцесс запускается при наличии активных настроек

### Критерий готовности
- [ ] Покрытие критичных путей в bot/llm.py
- [ ] Тесты не зависят от реальных API (мокирование)

---

## Задача 0.3: Создание ветки и тега

### Описание
Зафиксировать текущее состояние для возможности отката.

### Шаги
1. Создать тег текущего состояния: `git tag v0.9-pre-tools`
2. Создать ветку для работ: `git checkout -b feature/tool-calling`
3. Убедиться что CI (если есть) проходит на текущем состоянии

### Критерий готовности
- [ ] Тег создан и запушен
- [ ] Ветка создана
- [ ] Возможность отката к стабильному состоянию

---

## Задача 0.4: Подготовка структуры для новых модулей

### Описание
Создать пустые файлы и папки для новых модулей, чтобы импорты работали.

### Структура
```
LO_TG_BOT/
├── bot/
│   ├── llm.py                  # существующий
│   └── tool_calling.py         # НОВЫЙ (пустой пока)
│
├── tools/                      # НОВАЯ ПАПКА
│   └── __init__.py             # пустой
│
└── plugins/                    # НОВАЯ ПАПКА
    └── __init__.py             # пустой
```

### Критерий готовности
- [ ] Папка tools/ создана с __init__.py
- [ ] Папка plugins/ создана с __init__.py
- [ ] Файл bot/tool_calling.py создан (может быть пустой или с TODO)
- [ ] Импорты не ломают существующий код

---

# ФАЗА 1: Tool-Calling в LLM Engine

**Цель:** LLM может вызывать инструменты. Пока инструменты захардкожены в коде (2 тестовых).

**Срок:** 3-5 дней

**Принцип:** Минимальные изменения в существующем коде. Новая логика — в новых файлах.

---

## Обзор архитектуры Фазы 1

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  telegram_bot.py                                                            │
│  │                                                                          │
│  │  handle_message()                                                        │
│  │  ├── Собирает messages (system + history + user)                        │
│  │  ├── Вызывает get_reply(messages)          ← ИЗМЕНЕНИЕ                  │
│  │  └── Отправляет ответ пользователю                                      │
│  │                                                                          │
│  └──────────────────────────┬──────────────────────────────────────────────┘
│                             │
│                             ▼
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                                                                         │
│  │  llm.py — get_reply(messages, tools=None)         ← РАСШИРЕНИЕ          │
│  │  │                                                                      │
│  │  │  Если tools=None:                                                    │
│  │  │  └── Работает как раньше (без изменений)                            │
│  │  │                                                                      │
│  │  │  Если tools предоставлены:                                           │
│  │  │  └── Передаёт tools в LLM API                                       │
│  │  │  └── Возвращает (content, tool_calls)                               │
│  │  │                                                                      │
│  │  └──────────────────────────────────────────────────────────────────────┘
│                             │
│                             ▼
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                                                                         │
│  │  tool_calling.py — get_reply_with_tools(messages)       ← НОВЫЙ        │
│  │  │                                                                      │
│  │  │  1. Получает tools из HARDCODED_TOOLS                               │
│  │  │  2. Вызывает llm.get_reply(messages, tools)                         │
│  │  │  3. Если есть tool_calls:                                           │
│  │  │     ├── Выполняет инструменты                                       │
│  │  │     ├── Добавляет результаты в messages                             │
│  │  │     └── Повторяет запрос к LLM                                      │
│  │  │  4. Возвращает финальный текстовый ответ                            │
│  │  │                                                                      │
│  │  └──────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Задача 1.1: Расширение get_reply() для поддержки tools

### Описание
Модифицировать функцию `get_reply()` в `bot/llm.py` так, чтобы она могла принимать опциональный параметр `tools` и возвращать информацию о tool_calls.

### Текущая сигнатура
```python
async def get_reply(messages: List[dict]) -> str
```

### Новая сигнатура
```python
async def get_reply(
    messages: List[dict], 
    tools: List[dict] | None = None,
    tool_choice: str | None = "auto"
) -> tuple[str, List[ToolCall] | None]
```

### Поведение

**Без tools (обратная совместимость):**
- Если `tools=None`, функция работает как раньше
- Возвращает `(content, None)`

**С tools:**
- Передаёт `tools` и `tool_choice` в API LLM
- Если LLM вернул tool_calls, возвращает `(None, [ToolCall(...)])`
- Если LLM вернул текст, возвращает `(content, None)`

### Структура ToolCall
```python
@dataclass
class ToolCall:
    id: str              # Уникальный ID вызова (от LLM)
    name: str            # Имя инструмента
    arguments: dict      # Аргументы (уже распарсенный JSON)
```

### Изменения по провайдерам

#### OpenAI / OpenAI-compatible (Groq, OpenRouter, Ollama, etc.)
```
Request:
  tools: [...]
  tool_choice: "auto"

Response:
  message.tool_calls: [
    {
      id: "call_abc123",
      function: {
        name: "get_current_datetime",
        arguments: "{}"
      }
    }
  ]
```

#### Anthropic (Claude)
```
Request:
  tools: [...]  # Формат Anthropic отличается

Response:
  content: [
    {
      type: "tool_use",
      id: "toolu_01...",
      name: "get_current_datetime",
      input: {}
    }
  ]
```

#### Google (Gemini)
```
Request:
  tools: [...]  # Формат Gemini

Response:
  candidates[0].content.parts: [
    {
      function_call: {
        name: "get_current_datetime",
        args: {}
      }
    }
  ]
```

### Задачи
1. Добавить dataclass `ToolCall` в bot/llm.py (или отдельный models.py)
2. Модифицировать каждый провайдер для поддержки tools
3. Унифицировать парсинг tool_calls в ToolCall
4. Добавить конвертеры tools между форматами (если нужно)

### Критерий готовности
- [ ] get_reply() принимает опциональный параметр tools
- [ ] Без tools — работает как раньше (регрессии нет)
- [ ] С tools — возвращает ToolCall для OpenAI
- [ ] С tools — возвращает ToolCall для Anthropic
- [ ] С tools — возвращает ToolCall для Google
- [ ] Тесты на все варианты

---

## Задача 1.2: Создание модуля tool_calling.py

### Описание
Новый модуль, который оркестрирует процесс tool-calling: получает tools, вызывает LLM, выполняет инструменты, возвращает финальный ответ.

### Файл: bot/tool_calling.py

### Основная функция
```python
async def get_reply_with_tools(
    messages: List[dict],
    max_iterations: int = 5
) -> str
```

### Алгоритм работы

```
1. ПОДГОТОВКА
   │
   ├── Получить список tools (пока HARDCODED_TOOLS)
   ├── Если tools пустой → вызвать обычный get_reply() без tools
   │
2. ЦИКЛ TOOL-CALLING (max_iterations раз)
   │
   ├── Вызвать get_reply(messages, tools)
   │   │
   │   ├── Если вернулся текст (content) → ВЫХОД, вернуть content
   │   │
   │   └── Если вернулись tool_calls:
   │       │
   │       ├── Для каждого tool_call:
   │       │   ├── Найти handler по имени
   │       │   ├── Выполнить handler(arguments)
   │       │   └── Сохранить результат
   │       │
   │       ├── Добавить в messages:
   │       │   ├── assistant message с tool_calls
   │       │   └── tool result messages
   │       │
   │       └── Продолжить цикл
   │
3. ЗАЩИТА ОТ ЗАЦИКЛИВАНИЯ
   │
   └── Если достигнут max_iterations → вернуть fallback ответ
```

### Формат tool result message (OpenAI)
```python
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "2024-01-15 14:30:00"
}
```

### Формат tool result message (Anthropic)
```python
{
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_01...",
            "content": "2024-01-15 14:30:00"
        }
    ]
}
```

### Обработка ошибок

| Ситуация | Поведение |
|----------|-----------|
| Tool не найден | Вернуть error message в tool result |
| Tool выбросил исключение | Вернуть error message в tool result |
| Таймаут выполнения | Вернуть timeout error в tool result |
| Достигнут max_iterations | Вернуть текст: "Не удалось завершить операцию" |
| LLM API error | Пробросить исключение (как раньше) |

### Критерий готовности
- [ ] Функция get_reply_with_tools() реализована
- [ ] Цикл tool-calling работает
- [ ] Tool results правильно добавляются в messages
- [ ] Защита от бесконечного цикла
- [ ] Обработка ошибок выполнения tools
- [ ] Тесты на цикл tool-calling

---

## Задача 1.3: Захардкоженные тестовые инструменты

### Описание
Создать 2 простых инструмента прямо в коде для тестирования tool-calling. В Фазе 2 они будут вынесены в плагины.

### Инструмент 1: get_current_datetime

**Описание (для LLM, английский):**
```
Returns current date and time in ISO format with weekday name.
```

**Параметры:** Нет

**Поведение:**
- Возвращает текущую дату и время
- Формат: "2024-01-15 14:30:00 (Monday)"
- Использует UTC или локальное время (настраиваемо)

**Tool definition (OpenAI format):**
```json
{
  "type": "function",
  "function": {
    "name": "get_current_datetime",
    "description": "Returns current date and time in ISO format with weekday name",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  }
}
```

**Handler:**
```python
async def get_current_datetime() -> str:
    # Возвращает текущее время
```

### Инструмент 2: calculate

**Описание (для LLM, английский):**
```
Evaluates a mathematical expression and returns the result. 
Supports: +, -, *, /, **, parentheses, sqrt, sin, cos, tan, log, pi, e.
```

**Параметры:**
- `expression` (string, required) — математическое выражение

**Tool definition:**
```json
{
  "type": "function",
  "function": {
    "name": "calculate",
    "description": "Evaluates a mathematical expression and returns the result. Supports: +, -, *, /, **, parentheses, sqrt, sin, cos, tan, log, pi, e.",
    "parameters": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "Mathematical expression to evaluate, e.g. '2 + 2 * 3' or 'sqrt(16)'"
        }
      },
      "required": ["expression"]
    }
  }
}
```

**Handler:**
```python
async def calculate(expression: str) -> str:
    # Безопасный eval с ограниченным набором функций
    # Возвращает результат или сообщение об ошибке
```

**Безопасность:**
- Использовать ограниченный набор разрешённых функций
- Не использовать `eval()` напрямую
- Использовать `ast.literal_eval` или библиотеку `simpleeval`

### Структура в коде
```python
# bot/tool_calling.py

HARDCODED_TOOLS = [
    {
        "definition": { ... },  # OpenAI format
        "handler": get_current_datetime
    },
    {
        "definition": { ... },
        "handler": calculate
    }
]
```

### Критерий готовности
- [ ] get_current_datetime работает
- [ ] calculate работает с базовыми операциями
- [ ] calculate безопасен (нет code injection)
- [ ] Tool definitions корректны для OpenAI
- [ ] Тесты на оба инструмента

---

## Задача 1.4: Интеграция в telegram_bot.py

### Описание
Подключить tool-calling в обработчик сообщений. Должна быть возможность включать/выключать tool-calling.

### Текущий flow (упрощённо)
```python
# telegram_bot.py

async def handle_message(update, context):
    messages = build_messages(chat_id, text)
    reply = await get_reply(messages)
    await update.message.reply_text(reply)
    save_to_history(chat_id, text, reply)
```

### Новый flow
```python
# telegram_bot.py

async def handle_message(update, context):
    messages = build_messages(chat_id, text)
    
    if tools_enabled():  # Проверка флага
        reply = await get_reply_with_tools(messages)
    else:
        reply = await get_reply(messages)
    
    await update.message.reply_text(reply)
    save_to_history(chat_id, text, reply)
```

### Флаг включения tool-calling

**Варианты (выбрать один):**

1. **Переменная окружения:**
   ```
   ENABLE_TOOL_CALLING=true
   ```

2. **Настройка в БД (в LLM settings):**
   ```python
   llm_settings.enable_tools = True
   ```

3. **Всегда включено** (для Фазы 1, упрощение):
   ```python
   # Пока просто всегда используем tools
   reply = await get_reply_with_tools(messages)
   ```

**Рекомендация для Фазы 1:** Использовать переменную окружения `ENABLE_TOOL_CALLING=true`. Это позволяет быстро откатиться если что-то пойдёт не так.

### Обработка ошибок

Tool-calling не должен ломать бота. Если что-то пошло не так:
```python
try:
    reply = await get_reply_with_tools(messages)
except Exception as e:
    logger.error(f"Tool-calling failed: {e}, falling back to regular reply")
    reply = await get_reply(messages)  # Fallback
```

### Критерий готовности
- [ ] tool-calling интегрирован в telegram_bot.py
- [ ] Есть флаг для включения/выключения
- [ ] Fallback на обычный режим при ошибках
- [ ] Логирование tool-calls
- [ ] История диалога корректно сохраняется

---

## Задача 1.5: System prompt для tool-calling

### Описание
Обновить system prompt, чтобы LLM понимал как использовать инструменты и всегда отвечал на русском.

### Текущий system prompt
```
Ты — полезный ассистент. Отвечай на вопросы пользователя.
```

### Новый system prompt (английский для экономии токенов)
```
You are a helpful assistant in a Telegram bot.

IMPORTANT RULES:
1. Always respond in Russian, regardless of this prompt being in English.
2. You have access to tools. Use them when they can help answer the user's question.
3. For date/time questions, use the get_current_datetime tool.
4. For calculations, use the calculate tool.
5. If a tool returns an error, explain it to the user in a friendly way.
6. Do not mention that you're using tools unless the user asks.

Be concise and helpful.
```

### Где хранится

1. **Дефолтный** — в коде (bot/config.py или bot/tool_calling.py)
2. **Переопределённый** — в настройках LLM в БД (существующее поле systemPrompt)

### Логика
```python
def get_system_prompt():
    # 1. Проверить настройки в БД
    db_settings = get_llm_settings()
    if db_settings and db_settings.system_prompt:
        return db_settings.system_prompt
    
    # 2. Использовать дефолтный с tools
    return DEFAULT_SYSTEM_PROMPT_WITH_TOOLS
```

### Критерий готовности
- [ ] Новый system prompt создан
- [ ] Prompt на английском (экономия токенов)
- [ ] Инструкция отвечать на русском
- [ ] Prompt используется при tool-calling
- [ ] Можно переопределить через админку

---

## Задача 1.6: Тестирование Фазы 1

### Описание
Написать тесты для всех новых компонентов и провести ручное тестирование.

### Unit-тесты

#### test_tool_calling.py
```
test_get_current_datetime_returns_valid_format
test_calculate_basic_operations
test_calculate_with_functions (sqrt, sin, etc.)
test_calculate_handles_errors
test_calculate_safe_from_injection

test_get_reply_with_tools_no_tool_call
test_get_reply_with_tools_single_tool_call
test_get_reply_with_tools_multiple_tool_calls
test_get_reply_with_tools_max_iterations
test_get_reply_with_tools_tool_error_handling
```

#### test_llm_tools.py (расширение существующих)
```
test_get_reply_with_tools_openai
test_get_reply_with_tools_anthropic
test_get_reply_with_tools_google
test_get_reply_without_tools_unchanged
```

### Integration тесты

```
test_full_flow_datetime_question
test_full_flow_calculation_question
test_full_flow_regular_question_no_tools
test_fallback_on_tool_error
```

### Ручное тестирование (чеклист)

**Подготовка:**
- [ ] Бот запущен с `ENABLE_TOOL_CALLING=true`
- [ ] LLM настроен (OpenAI или другой с поддержкой tools)

**Тесты datetime:**
- [ ] "Сколько сейчас времени?" → ответ с текущим временем
- [ ] "Какой сегодня день недели?" → правильный день
- [ ] "What time is it?" → ответ на русском с временем

**Тесты calculate:**
- [ ] "Посчитай 2+2" → "4"
- [ ] "Сколько будет 15% от 200?" → "30"
- [ ] "Чему равен квадратный корень из 144?" → "12"
- [ ] "sin(0) + cos(0)" → "1"

**Тесты без tools:**
- [ ] "Привет, как дела?" → обычный ответ (без вызова tools)
- [ ] "Расскажи анекдот" → обычный ответ

**Тесты ошибок:**
- [ ] "Посчитай 1/0" → понятное сообщение об ошибке
- [ ] "Посчитай abc" → понятное сообщение об ошибке

**Тесты совместимости:**
- [ ] История диалога работает
- [ ] Бот не падает при длинных диалогах
- [ ] Админка работает как раньше

### Критерий готовности
- [ ] Все unit-тесты проходят
- [ ] Integration тесты проходят
- [ ] Ручное тестирование пройдено
- [ ] Нет регрессий в существующей функциональности

---

## Последовательность работ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 1: Фаза 0                                                             │
│                                                                             │
│  Утро:                                                                      │
│  ├── 0.1 Ревью текущего состояния                                          │
│  └── 0.2 Дополнение тестов (если нужно)                                    │
│                                                                             │
│  После обеда:                                                               │
│  ├── 0.3 Создание ветки и тега                                             │
│  └── 0.4 Подготовка структуры для новых модулей                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 2: Задача 1.1 — Расширение get_reply()                               │
│                                                                             │
│  ├── Добавить ToolCall dataclass                                           │
│  ├── Модифицировать OpenAI провайдер                                       │
│  ├── Модифицировать Anthropic провайдер                                    │
│  ├── Модифицировать Google провайдер                                       │
│  └── Тесты                                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 3: Задачи 1.2 + 1.3 — tool_calling.py + инструменты                  │
│                                                                             │
│  Утро:                                                                      │
│  ├── Создать bot/tool_calling.py                                           │
│  ├── Реализовать get_reply_with_tools()                                    │
│  └── Цикл tool-calling                                                     │
│                                                                             │
│  После обеда:                                                               │
│  ├── Реализовать get_current_datetime                                      │
│  ├── Реализовать calculate                                                 │
│  └── Тесты инструментов                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 4: Задачи 1.4 + 1.5 — Интеграция + System prompt                     │
│                                                                             │
│  Утро:                                                                      │
│  ├── Интеграция в telegram_bot.py                                          │
│  ├── Флаг ENABLE_TOOL_CALLING                                              │
│  └── Fallback логика                                                       │
│                                                                             │
│  После обеда:                                                               │
│  ├── Новый system prompt                                                   │
│  ├── Логирование tool-calls                                                │
│  └── Тесты интеграции                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ДЕНЬ 5: Задача 1.6 — Тестирование                                         │
│                                                                             │
│  ├── Дописать unit-тесты                                                   │
│  ├── Integration тесты                                                     │
│  ├── Ручное тестирование по чеклисту                                       │
│  ├── Исправление багов                                                     │
│  └── Документация изменений                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  РЕЗУЛЬТАТ ФАЗЫ 1                                                          │
│                                                                             │
│  ✅ Бот умеет использовать инструменты                                     │
│  ✅ 2 тестовых инструмента работают (datetime, calculator)                 │
│  ✅ Tool-calling работает для OpenAI, Anthropic, Google                    │
│  ✅ Можно включить/выключить через env                                     │
│  ✅ Текущая функциональность не сломана                                    │
│  ✅ Готов фундамент для Фазы 2 (Plugin System)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| LLM не вызывает tools | Средняя | Высокое | Улучшить system prompt, проверить формат tools |
| Разные форматы tool-calling у провайдеров | Высокая | Среднее | Абстракция ToolCall, конвертеры |
| Tool-calling замедляет ответы | Средняя | Среднее | Флаг отключения, логирование времени |
| calculate небезопасен | Низкая | Высокое | Использовать simpleeval, тесты на injection |
| Регрессии в существующем коде | Средняя | Высокое | Тесты, fallback, постепенная интеграция |

---

## Definition of Done для Фазы 1

- [ ] Все задачи 0.1-0.4 выполнены
- [ ] Все задачи 1.1-1.6 выполнены
- [ ] Все unit-тесты проходят
- [ ] Ручное тестирование пройдено
- [ ] Нет регрессий (существующие тесты проходят)
- [ ] Код отревьюен
- [ ] Ветка готова к мержу (или продолжению в Фазе 2)
- [ ] Документация обновлена (README, CURRENT_IMPLEMENTATION.md)

---

## Версионирование документа

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0 | 2026-02-06 | Первая версия плана Фаз 0-1 |
