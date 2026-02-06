# PHASE 6: Worklog Checker (business plugin)

> **Detailed task specification for Phase 6**  
> First business plugin: check employee worklogs via Jira and Tempo

**Version:** 1.0  
**Date:** 2026-02-06  
**Estimated duration:** 1–2 weeks  
**Prerequisite:** Phases 0–4 completed (Plugin System, Storage, API, Admin "Tools" are working)

---

## Related documents

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target system architecture | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Full task breakdown (block 7.1) | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Detailed plan for Phase 0–1 | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Detailed plan for Phase 2 | ✅ Current (in progress) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Detailed plan for Phase 3 | ✅ Current (in progress) |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Detailed plan for Phase 4 | ✅ Current (in progress) |
| [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Detailed plan for Phase 5 | ✅ Current (in progress) |
| [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Detailed plan for Phase 6 (this document) | ✅ Current (in progress) |

---

## Phase navigation

| Phase | Document | Description | Status |
|-------|----------|-------------|--------|
| 0-1 | [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Stabilization + Tool-Calling | ✅ Current (in progress) |
| 2 | [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Plugin System | ✅ Current (in progress) |
| 3 | [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Storage + API | ✅ Current (in progress) |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Admin Tools | ✅ Current (in progress) |
| 5 | [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Admin Administrators | ✅ Current (in progress) |
| 6 | **[PLAN_PHASE_6.md](PLAN_PHASE_6.md)** | Worklog Checker | ✅ Current (in progress) |

### Current implementation (v1.0)

| Document | Description |
|----------|-------------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Current implementation specification |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

---

## Overall goal of Phase 6

**Before:** The system has plugins (calculator, datetime_tools), tools are configured via the admin panel, but there are no business integrations.

**After:** The **Worklog Checker** plugin is added. On user request (via the bot) it checks employee worklogs for a period: fetches data from Jira (user, issues) and Tempo (actual hours), compares with the required norm, and returns a summary (deficit/overtime, task list).

**Important:**

- The plugin follows the standard (plugin.yaml, handlers.py); settings are stored in the DB via the shared mechanism (Phase 3).
- External calls are only to Jira REST API and Tempo API (or Tempo Reports API depending on the chosen API version).
- This document defines **specifications and task descriptions only**, with no code implementation.

---

## Наvalue plugin

- **Пользователь in Telegram:** «Проверь ворклогand Иванова за эту неделю» / «Summary by команде за месяц».
- **Бот:** вызывает инструмент плагиon with параметрамand (сотрудник/команда, период).
- **Плагин:** запрашивает настройкand (Jira URL, токены), обращается к Jira and Tempo, считает норму часоin за период (with учётом рабочих дней and требуемых часоin in день), возвращает структурированный result.
- **LLM:** форматирует ответ пользователю on естественном языке.

---

## Внешние системы

### Jira (Cloud or Server/Data Center)

- **Наvalue:** получение пользователя by имени/email (поиск), прand необходимостand — list tasks пользователя за период (для контекста).
- **Аутентификация:** Jira Cloud — API Token + email; Jira Server — Personal Access Token or Basic (user/token). В спецификациand учитывать оба варианта (in настройках плагиon — отдельные поля прand необходимости).
- **Типовые запросы:**
  - Поиск пользователя: REST API (например, пользователь by displayName or by accountId, in зависимостand от версиand Jira).
  - Список tasks (опционально): JQL by assignee and датам.
- **Documentация:** [Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/).

### Tempo (Tempo Timesheets / Tempo API)

- **Наvalue:** получение ворклогоin (worklogs) за период для пользователя (by accountId or user key).
- **Аутентификация:** API Token (Tempo API token in настройках аккаунта).
- **Типовые запросы:**
  - Worklogs за период: эндпоинт вида `/worklogs` with параметрамand user (or accountId), from, to.
- **Documentация:** [Tempo API](https://apidocs.tempo.io/) (актуальную версию уточнять by официальному сайту Tempo).

**Important:** Версиand API Jira Cloud and Tempo могут отличаться (v2/v3, OAuth vs token). В спецификациand зафиксировать: поддержка Jira Cloud + Tempo API with токенами; прand необходимостand отдельный подраздел «Ограничения and варианты (Jira Server)».

---

## Structure plugin

### Каталог and файлы

```
plugins/
└── worklog_checker/
    ├── plugin.yaml          # Манифест: id, name, version, tools, settings
    ├── handlers.py          # Обработчикand инструментоin (check_worklogs, get_worklog_summary)
    ├── jira_client.py       # [Вспомогательный] Клиент Jira REST API
    ├── tempo_client.py      # [Вспомогательный] Клиент Tempo API
    └── (опционально) test_connection.py  # Проверка подключения для кнопкand in админке
```

### plugin.yaml — манифест

Спецификация содержимого (без реализации):

- **id:** `worklog-checker`
- **name:** «Проверка ворклогов» (or «Worklog Checker»)
- **version:** `1.0.0`
- **enabled by умолчанию:** `false` (плагин требует настройкand Jira/Tempo)
- **tools:**
  - **check_worklogs**
    - **description:** on английском, for LLM: проверка ворклогоin сотрудника за период; возвращает залогированные часы, норму, дефицит/переработку, list tasks (кратко).
    - **parameters (JSON Schema):**
      - `employee` (string, required): имя/фамилия/email сотрудника or часть для поиска in Jira.
      - `period` (string, required): период, например `this_week`, `last_week`, `this_month`, `last_month` or даты in формате `YYYY-MM-DD/YYYY-MM-DD`.
    - **timeout:** 60 (секунд)
  - **get_worklog_summary**
    - **description:** сводка by ворклогам команды/нескольких сотрудникоin за период (суммы by людям, общая картина).
    - **parameters:**
      - `team` (string, optional): название команды or перечень имён/идентификатороin (формат уточняется — list через запятую or one идентификатор группы in Jira).
      - `period` (string, required): тот же формат, that and in check_worklogs.
    - **timeout:** 90
- **settings (схема для админкand and валидации):**
  - `jira_url` (string, required): базовый URL Jira, например `https://company.atlassian.net`
  - `jira_email` (string, required для Cloud): email для Jira Cloud API token
  - `jira_token` (password, required): API Token (Cloud) or PAT (Server)
  - `tempo_token` (password, required): Tempo API token
  - `required_hours_per_day` (number, optional): норма часоin in день (by умолчанию 8)
  - `working_days` (string, optional): рабочие дни, например `mon,tue,wed,thu,fri` (by умолчанию пн–пт)

On необходимостand in манифесте указывается наличие **test handler** для кнопкand «Check подключение» in админке (см. ниже).

---

## Tools — спецификация поведения

### 1. check_worklogs(employee, period)

- **Вход:** `employee` (строка), `period` (строка).
- **Логика (пошагово):**
  1. Загрузка настроек плагиon (get_plugin_settings).
  2. Парсинг периода: преобразование `this_week` / `last_week` / `this_month` / `last_month` in даты начала and конца (by локальной таймзоnot or UTC — зафиксировать in спеках).
  3. Поиск пользователя in Jira by `employee` (displayName, email or accountId — in зависимостand от API).
  4. Получение ворклогоin from Tempo для найденного пользователя за период (from, to).
  5. Расчёт нормы часов: число рабочих дней in периоде × required_hours_per_day (working_days учитываются).
  6. Суммирование фактических часоin from ворклогов.
  7. Формирование resultа: employee (display name), period (диапазон дат), logged_hours, required_hours, deficit_or_surplus (дефицит/переработка), list tasks (ключ tasksи, сумма часоin by tasksе) — структура для JSON.
- **Выход:** строка (сериализованный JSON or читаемый текст) для возврата in LLM; прand ошибке — error message (без падения процесса).
- **Ошибки:** пользователь not найден, нет доступа к Tempo/Jira, таймаут — обрабатываются and возвращаются as текст ошибкand in ответе tool.

### 2. get_worklog_summary(team, period)

- **Вход:** `team` (опционально), `period` (обязательно).
- **Логика:**
  1. Загрузка настроек, парсинг периода.
  2. Определение списка пользователей: еслand `team` задан — разрешение команды in list пользователей (через Jira API группы/проекта or заранее заданный list in настройках — уточнить in спеках); еслand not задан — by возможностand all пользователand with ворклогамand за период (or ограниченный список).
  3. For каждого пользователя — запроwith ворклогоin за период (Tempo).
  4. Агрегация: by каждому сотруднику — logged_hours, required_hours, deficit; общая сводка by периоду.
- **Выход:** структурированный result (JSON-подобная строка or dict, сериализованный in строку).
- **Ошибки:** те же принципы, that and для check_worklogs.

Спецификация not предписывает конкретный формат JSON-полей (имеon ключей), но он должен быть зафиксирован in этом документе or in отдельном «Контракт ответа» внутрand Фазы 6, чтобы LLM and tests моглand on него опираться.

---

## Вспомогательные модулand (контракт, без реализации)

### jira_client

- **Наvalue:** обёртка над HTTP-запросамand к Jira REST API.
- **Методы (контракт):**
  - **search_user(query: str) -> dict | None:** поиск пользователя by имени/email; возвращает объект with полями, необходимымand для Tempo (например accountId, displayName).
  - **get_issues_for_user(account_id: str, date_from, date_to) -> list[dict] (опционально):** list tasks пользователя за период (еслand нужен для обогащения ответа).
- **Аутентификация:** from настроек плагиon (jira_url, jira_email, jira_token or аналог для Server).
- **Error handling:** HTTP 401/403/404 — логирование and выброwith исключения or возврат None/пустого списка by соглашению; таймауты — обрабатывать and not ронять процесс.

### tempo_client

- **Наvalue:** обёртка над Tempo API (worklogs).
- **Методы (контракт):**
  - **get_worklogs(user_identifier: str, date_from, date_to) -> list[dict]:** ворклогand пользователя за период. `user_identifier` — accountId (Jira Cloud) or user key (Jira Server); формат дат — by документациand Tempo.
  - Каждый элемент списка содержит as минимум: ключ tasksand (issue key), часы (or секунды — привестand к часам in логике plugin), дату.
- **Аутентификация:** tempo_token from настроек.
- **Error handling:** аналогично jira_client.

Конкретные URL эндпоинтоin (Tempo v2/v3 etc.) указать in спеках or in отдельной таблице «Эндпоинты» in этом документе, чтобы реализация была однозначной.

---

## Проверка подключения (test handler)

- **Наvalue:** для кнопкand «Check подключение» in админке (еслand плагин поддерживает test in plugin.yaml).
- **Behaviour:** one запроwith к Jira (например, current пользователь or поиск by фиксированной строке) and one запроwith к Tempo (минимальный диапазон дат or проверка токена). Результат: `{ "jira_ok": true|false, "tempo_ok": true|false, "errors": [...] }`.
- **Возврат:** строка (JSON) or dict — by соглашению with общим механизмом test in админке.

---

## Phase 6 (декомпозиция)

Задачand ниже — постановкand для реализации, без написания кода.

---

### Task 6.1: Манифест and структура plugin

- Description: создать каталог `plugins/worklog_checker`, файл `plugin.yaml` by спецификациand выше (id, name, version, tools with параметрамand and timeout, settings with типамand and required).
- Done when: плагин подхватывается Plugin Loader, in Registry отображаются two tool (check_worklogs, get_worklog_summary), in админке отображаются настройкand plugin; прand отсутствиand настроек tools in статусе «требует настройки».

---

### Task 6.2: Jira client (контракт and реализация)

- Description: реализовать модуль `jira_client` with методамand search_user and прand необходимостand get_issues_for_user; аутентификация and обработка errors by спекам.
- Done when: by имени/email возвращается пользователь with accountId/displayName; ошибкand 401/403/404 and таймауты обрабатываются без падения процесса.

---

### Task 6.3: Tempo client (контракт and реализация)

- Description: реализовать модуль `tempo_client` with методом get_worklogs; аутентификация and обработка errors.
- Done when: by user identifier and периоду возвращается list ворклогоin with полямand issue key and часы; ошибкand обрабатываются.

---

### Task 6.4: Парсинг периода (period)

- Description: function преобразования строкand периода (`this_week`, `last_week`, `this_month`, `last_month`, `YYYY-MM-DD/YYYY-MM-DD`) in даты начала and конца (date_from, date_to). Учесть working_days and таймзону (UTC or локальную — зафиксировать).
- Done when: для каждой допустимой строкand периода возвращается корректный диапазон дат; невалидный формат обрабатывается with понятной ошибкой.

---

### Task 6.5: Обработчик check_worklogs

- Description: in handlers.py реализовать асинхронный обработчик check_worklogs(employee, period): загрузка настроек, поиск пользователя (Jira), получение ворклогоin (Tempo), расчёт нормы and дефицита/переработки, формирование resultа in согласованном формате (JSON-строка or текст).
- Done when: вызоin from бота/LLM with параметрамand employee and period возвращает осмысленный result; прand отсутствиand пользователя or ошибке API возвращается error message in формате ответа tool.

---

### Task 6.6: Обработчик get_worklog_summary

- Description: реализовать get_worklog_summary(team, period) by спекам: определение списка пользователей (by team or иному правилу), агрегация ворклогов, сводка by сотрудникам and общая.
- Done when: вызоin with period возвращает сводку; прand заданиand team (еслand реализовано) — фильтрация by команде; ошибкand обрабатываются.

---

### Task 6.7: Test handler (опционально)

- Description: реализовать проверку подключения к Jira and Tempo (отдельная function or handler), зарегистрировать in plugin.yaml as test (еслand стандарт плагиноin это поддерживает).
- Done when: in админке кнопка «Check подключение» для плагиon Worklog Checker возвращает result вида jira_ok, tempo_ok, errors.

---

### Task 6.8: Documentация and контракты ответов

- Description: зафиксировать in docs or in комментариях плагиon формат возвращаемых структур (check_worklogs, get_worklog_summary) and list поддерживаемых значений period; прand необходимостand — table эндпоинтоin Jira/Tempo with версиямand API.
- Done when: разработчик and tests могут опираться on описание формата ответа and периодов.

---

### Task 6.9: Ручное and E2E тестирование

- Description: сценарии: добавление plugin, настройка Jira/Tempo in админке, проверка подключения, запроwith from бота «Проверь ворклогand [имя] за эту неделю» and «Summary за месяц», проверка ответа LLM and отсутствия падений прand errorх (неверный токен, пользователь not найден).
- Done when: all сценариand пройдены; прand errorх API пользователь получает понятное сообщение, а not сырой traceback.

---

## Work sequence

```
Неделя 1:
├── 6.1 Манифест and структура plugin
├── 6.2 Jira client
├── 6.3 Tempo client
└── 6.4 Парсинг периода

Неделя 2:
├── 6.5 Обработчик check_worklogs
├── 6.6 Обработчик get_worklog_summary
├── 6.7 Test handler (опционально)
├── 6.8 Documentация and контракты
└── 6.9 Тестирование
```

---

## Definition of Done for Phase 6

- [ ] Плагин worklog_checker загружается and отображается in админке
- [ ] Settings (Jira URL, токены, часы, рабочие дни) сохраняются and используются
- [ ] Инструмент check_worklogs возвращает ворклогand and дефицит/переработку за период
- [ ] Инструмент get_worklog_summary возвращает сводку (by команде or за период)
- [ ] Ошибкand Jira/Tempo обрабатываются and not роняют процесс
- [ ] Проверка подключения from админкand работает (еслand реализован test handler)
- [ ] Ручное/E2E тестирование пройдено

---

## Рискand and ограничения

- **Версиand API:** Jira Cloud REST API v3 and Tempo API могут менять эндпоинты; зафиксировать поддерживаемые версиand in документациand plugin.
- **Jira Server:** прand необходимостand поддержкand Server — отдельная ветка настроек (другой тип аутентификации) and тесты.
- **Лимиты Tempo/Jira:** прand большом количестве ворклогоin может потребоваться пагинация; учесть in контракте tempo_client and in обработчиках.
- **Таймзоны:** единая политика (UTC or локальная таймзоon сервера) для расчёта «рабочих дней» and периодоin — зафиксировать in спеках.

---

## Out of scope in Фазу 6

- Другие бизнес-plugins (HR Service, Reminder)
- Изменения in ядре Plugin System (кроме возможных доработок by test handler, еслand онand потребуются)
- Автоматическая отправка напоминаний (это плагин Reminder)
- Поддержка Jira Server без предварительной фиксациand требований in отдельной спецификации

---

## Document versioning

| Version | Date | Description |
|--------|------|----------|
| 1.0 | 2026-02-06 | First version detailed planа Фазы 6 |
