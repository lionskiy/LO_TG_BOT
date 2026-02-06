# PHASE 5: Admin "Administrators"

> **Detailed task breakdown for Phase 5**  
> UI for managing администраторамand сервиса (service admins)

**Version:** 1.0  
**Date:** 2026-02-06  
**Estimated duration:** 3–5 дней  
**Prerequisite:** For единой навигациand желательно завершение Фазы 4 (пункт меню «Administrators» добавляется там). API уже есть in v1.0 — прand необходимостand Фазу 5 можно выполнять параллельно with 4/6 and добавить пункт меню in рамках this фазы.

---

## Related documents

| Document | Description | Status |
|----------|----------|--------|
| [ARCHITECTURE_BLUEPRINT.md](ARCHITECTURE_BLUEPRINT.md) | Target system architecture | ✅ Current (in progress) |
| [UPGRADE_TASKS.md](UPGRADE_TASKS.md) | Task breakdown | ✅ Current (in progress) |
| [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Phase 0-1 | ✅ Current (in progress) |
| [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Phase 2 | ✅ Current (in progress) |
| [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Phase 3 | ✅ Current (in progress) |
| [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Phase 4 | ✅ Current (in progress) |
| [PLAN_PHASE_5.md](PLAN_PHASE_5.md) | Phase 5 (this document) | ✅ Current (in progress) |
| [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Phase 6 (next) | ✅ Current (in progress) |

---

## Phase navigation

| Phase | Document | Description | Status |
|------|----------|----------|--------|
| 0-1 | [PLAN_PHASE_0_1.md](PLAN_PHASE_0_1.md) | Stabilization + Tool-Calling | ✅ Current (in progress) |
| 2 | [PLAN_PHASE_2.md](PLAN_PHASE_2.md) | Plugin System | ✅ Current (in progress) |
| 3 | [PLAN_PHASE_3.md](PLAN_PHASE_3.md) | Storage + API | ✅ Current (in progress) |
| 4 | [PLAN_PHASE_4.md](PLAN_PHASE_4.md) | Admin Tools | ✅ Current (in progress) |
| 5 | **[PLAN_PHASE_5.md](PLAN_PHASE_5.md)** | Admin Administrators | ✅ Current (in progress) |
| 6 | [PLAN_PHASE_6.md](PLAN_PHASE_6.md) | Worklog Checker | ✅ Current (in progress) |

### Current implementation (v1.0)

| Document | Description |
|----------|----------|
| [TG_Project_Helper_v1.0.md](TG_Project_Helper_v1.0.md) | Спецификация (API `/api/service-admins/*` уже реализован) |
| [TG_Project_Helper_v1.0_QUICKSTART.md](TG_Project_Helper_v1.0_QUICKSTART.md) | Quick start and FAQ |

---

## Phase 5

**Было:** API for managing администраторамand сервиса уже реализован (`/api/service-admins/*`), но управлять списком можно только через Swagger or curl.

**After:** В админке появляется полноценный раздел «Administrators» with UI: просмотр списка, добавление by Telegram ID, обновление профиля from Telegram, удаление with подтверждением.

**Important:**

- Используется existing стек (vanilla JS, fetch API).
- Стилистика консистентon with разделамand «Settings» and «Tools».
- Бэкенд **not меняется** — all эндпоинты уже есть.

---

## Существующий API (референс)

All эндпоинты защищены заголовком `X-Admin-Key` (еслand задан `ADMIN_API_KEY`).

| Метод | Путь | Description |
|-------|------|----------|
| GET | `/api/service-admins` | Список администраторов. Ответ: `{ admins: ServiceAdminResponse[], total: number }` |
| POST | `/api/service-admins` | Add администратора. Body: `{ telegram_id: number }`. Ответ: `ServiceAdminResponse`. 409 еслand уже есть. |
| GET | `/api/service-admins/{telegram_id}` | Один администратор by Telegram ID. 404 еслand not найден. |
| DELETE | `/api/service-admins/{telegram_id}` | Delete администратора. 204 прand успехе, 404 еслand not найден. |
| POST | `/api/service-admins/{telegram_id}/refresh` | Update профиль from Telegram. Ответ: `ServiceAdminResponse`. 404 еслand not найден. |

### Модель ServiceAdminResponse

| Поле | Тип | Description |
|------|-----|----------|
| id | number | Внутренний ID записand |
| telegram_id | number | Telegram user ID |
| first_name | string \| null | Имя from профиля Telegram |
| last_name | string \| null | Фамилия from профиля Telegram |
| username | string \| null | @username from Telegram |
| display_name | string | Отображаемое имя (first_name + last_name or username or "ID: {telegram_id}") |
| is_active | boolean | Активен лand администратор |
| created_at | string (ISO 8601) | Date добавления |

---

## Design requirements

### Необходимые макеты (опционально)

| # | Screen | Description | Priority |
|---|-------|----------|-----------|
| 1 | Список администратороin | Таблица + кнопка «Добавить» | Средний |
| 2 | Модалка добавления | Поле Telegram ID + подсказка | Средний |
| 3 | Модалка подтверждения удаления | Текст + кнопкand Delete / Отмеon | Низкий |

On отсутствиand макетоin — ориентироваться on существующие разделы админкand (таблицы, модалки, кнопки).

---

## UI architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Admin Panel                                                                │
│                                                                             │
│  ┌─────────────┐  ┌───────────────────────────────────────────────────────┐ │
│  │  Navigation  │  │  #admins → Administrators          [PHASE 5]          │ │
│  │             │  │                                                       │ │
│  │  Settings  │  │  • Header "Administrators"                        │ │
│  │  Tools│  │  • Кнопка "+ Добавить"                              │ │
│  │  Администр. │  │  • Таблица: ID, Имя, Username, Date добавления       │ │
│  │   (активен) │  │  • Действия: Update профиль, Delete               │ │
│  │             │  │  • Пустое состояние: "Нет администраторов"           │ │
│  └─────────────┘  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Файловая структура

```
admin/
├── index.html          # [EXTENSION] Контейнер раздела #admins (еслand ещё not добавлен)
├── styles.css          # [EXTENSION] Стor для раздела Administrators
├── app.js              # [EXTENSION] Роутинг #admins → показ раздела
└── admins.js           # [NEW] Логика раздела «Administrators»
```

If in Фазе 4 раздел «Administrators» реализован as заглушка (пустой контейнер), in Фазе 5 in this контейнер подключается содержимое from `admins.js`.

---

# UI-спецификации

---

## Screen 1: Список администраторов

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Administrators                                    [+ Добавить]             │
│                                                                             │
│  Administrators сервиса имеют доступ к админ-панелand (прand вводе Admin key).  │
│  Добавляются by Telegram ID.                                                │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Telegram ID   │  Имя / Display name   │  Username   │  Добавлен    │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  365491351     │  Владимир Ленский      │  @vlensky   │  05.02.2026  │  │
│  │                │                        │             │  [Обновить]  │  │
│  │                │                        │             │  [Удалить]  │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  123456789     │  ID: 123456789         │  —          │  01.02.2026  │  │
│  │                │  (профиль not получен)  │             │  [Обновить]  │  │
│  │                │                        │             │  [Удалить]  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Total: 2                                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Пустое состояние

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Administrators                                    [+ Добавить]             │
│                                                                             │
│  Нет администраторов. Нажмите «Добавить», чтобы добавить первого.          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Behaviour

- On открытиand раздела (#admins) вызывается `GET /api/service-admins`.
- Данные отображаются in таблице.
- Колонки: Telegram ID, Имя (display_name), Username (or «—»), Date добавления (форматированная), Действия.
- В строке действий: кнопка «Обновить» (refresh), кнопка «Удалить» (danger).
- If list пуст — показывается текст пустого состояния.

---

## Screen 2: Модалка «Add администратора»

### Wireframe

```
┌─────────────────────────────────────────────────────────┐
│  Add администратора                           [×]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Telegram ID *                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 365491351                                            ││
│  └─────────────────────────────────────────────────────┘│
│  Узнать свой ID: напишите боту @userinfobot in Telegram  │
│                                                         │
│                              [Отмена]  [Добавить]       │
└─────────────────────────────────────────────────────────┘
```

### Behaviour

- Кнопка «+ Добавить» открывает модалку.
- Поле «Telegram ID» — число, обязательное. Валидация: целое положительное число.
- Под полем — подсказка: «Узнать свой ID: напишите боту @userinfobot in Telegram».
- «Отмена» / крестик / клик by backdrop — закрытие без сохранения.
- «Добавить» — отправка `POST /api/service-admins` with `{ telegram_id: number }`.
  - Успех (201): закрыть модалку, toast «Администратор добавлен», обновить список.
  - 409: toast «Этот пользователь уже является администратором».
  - 400: toast with текстом ошибкand (например, неверный telegram_id).
  - Сеть/error: toast «Ошибка прand добавлении».

---

## Screen 3: Модалка подтверждения удаления

### Wireframe

```
┌─────────────────────────────────────────────────────────┐
│  Delete администратора                            [×]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Вы уверены, that хотите удалить администратора          │
│  Владимир Ленский (@vlensky)?                           │
│                                                         │
│  Он потеряет доступ к админ-панели.                      │
│                                                         │
│                              [Отмена]  [Удалить]         │
└─────────────────────────────────────────────────────────┘
```

### Behaviour

- Кнопка «Удалить» in строке tables открывает модалку подтверждения.
- В тексте подставляются display_name and username (еслand есть), иначе «ID: {telegram_id}».
- «Удалить» — `DELETE /api/service-admins/{telegram_id}`.
  - Успех (204): закрыть модалку, toast «Администратор удалён», обновить список.
  - 404: toast «Администратор not найден», закрыть модалку, обновить список.

---

## Действие «Update профиль»

- Кнопка «Обновить» in строке — `POST /api/service-admins/{telegram_id}/refresh`.
- Во время запроса кнопку можно показать in состояниand loading (опционально).
- Успех: toast «Профиль обновлён», обновить строку or весь список.
- Ошибка: toast with сообщением об ошибке.

---

# Phase 5

---

## Task 5.1: Контейнер and роутинг

### Description

Убедиться, that in админке есть контейнер для раздела «Administrators» and прand переходе by #admins отображается this раздел (остальные скрыты).

### Что сделать

1. В `index.html` — блок with `id="section-admins"` (or аналогичным), изначально скрыт.
2. В `app.js` — прand hash `#admins` показывать `section-admins`, скрывать остальные разделы, подсвечивать пункт меню «Administrators».

### Файлы

- `admin/index.html`
- `admin/app.js`

### Done when

- [ ] Переход by #admins открывает раздел «Administrators»
- [ ] Пункт меню «Administrators» подсвечивается
- [ ] Остальные разделы скрыты

---

## Task 5.2: API-функциand (admins.js)

### Description

Implement in `admins.js` функциand для работы with API (with учётом Admin key from конфига админки).

### Что сделать

1. `loadAdmins()` — GET /api/service-admins, возвращает список.
2. `addAdmin(telegramId)` — POST /api/service-admins, body `{ telegram_id }`, возвращает созданного адмиon or бросает by статусу.
3. `deleteAdmin(telegramId)` — DELETE /api/service-admins/{telegram_id}.
4. `refreshAdmin(telegramId)` — POST /api/service-admins/{telegram_id}/refresh.
5. Использовать common метод запросоin with заголовком X-Admin-Key (as in существующем app.js для настроек).

### Файлы

- `admin/admins.js`

### Done when

- [ ] All четыре метода вызывают корректные эндпоинты
- [ ] Header авторизациand передаётся
- [ ] Ошибкand (4xx, 5xx) обрабатываются and пробрасываются для показа in UI

---

## Task 5.3: Отображение списка

### Description

On открытиand раздела загружать list администратороin and отображать его in таблице.

### Что сделать

1. On показе раздела #admins вызывать loadAdmins().
2. Отрисовка таблицы: колонкand Telegram ID, Имя (display_name), Username, Date добавления, Действия.
3. Форматирование даты created_at (локальная дата or ISO on выбор).
4. Пустое состояние: еслand admins.length === 0 — показать текст «Нет администраторов» and подсказку добавить первого.
5. В колонке «Действия» — кнопкand «Обновить» and «Удалить» для каждой строки.

### Файлы

- `admin/admins.js`
- `admin/index.html` (разметка таблицы, прand необходимости)

### Done when

- [ ] Список загружается and отображается
- [ ] Пустое состояние отображается прand отсутствиand админов
- [ ] Кнопкand «Обновить» and «Удалить» присутствуют in каждой строке

---

## Task 5.4: Модалка добавления

### Description

Модальное окно для добавления администратора by Telegram ID.

### Что сделать

1. HTML-разметка модалки: заголовок, поле Telegram ID (number input), подсказка про @userinfobot, кнопкand Отмеon / Добавить.
2. Открытие by кнопке «+ Добавить», закрытие by крестику, кнопке «Отмена» and клику by backdrop.
3. Валидация: Telegram ID — целое положительное число.
4. Отправка POST прand нажатиand «Добавить», обработка 201 / 409 / 400 and сетевых errors, toast and обновление списка прand успехе.

### Файлы

- `admin/index.html` or `admin/admins.js` (разметка модалкand может генерироваться from JS)
- `admin/admins.js`
- `admin/styles.css` (стor модалки, еслand ещё not общие)

### Done when

- [ ] Модалка открывается and закрывается
- [ ] Валидация срабатывает
- [ ] Успешное добавление закрывает модалку and обновляет список
- [ ] Ошибкand 409 and 400 отображаются in toast

---

## Task 5.5: Модалка подтверждения удаления

### Description

Модальное окно подтверждения перед удалением администратора.

### Что сделать

1. Разметка: текст «Delete администратора {display_name} (@username)?» (or «ID: {telegram_id}»), пояснение про потерю доступа, кнопкand Отмеon / Удалить.
2. On нажатиand «Удалить» in таблице открывать модалку, передавая in неё текущую строку (telegram_id, display_name, username).
3. Кнопка «Удалить» in модалке — DELETE запрос, прand 204 — закрытие, toast, обновление списка.
4. On 404 — toast and обновление списка.

### Файлы

- `admin/admins.js`
- `admin/index.html` or генерируемая разметка
- `admin/styles.css`

### Done when

- [ ] Модалка показывает имя/username удаляемого
- [ ] Delete выполняется and list обновляется
- [ ] Отмеon закрывает модалку без запроса

---

## Task 5.6: Действие «Update профиль»

### Description

Обработчик кнопкand «Обновить» in строке таблицы.

### Что сделать

1. По клику вызывать refreshAdmin(telegram_id).
2. On успехе — toast «Профиль обновлён», обновить данные in строке or перезагрузить список.
3. On ошибке — toast with сообщением.

### Файлы

- `admin/admins.js`

### Done when

- [ ] Запроwith отправляется
- [ ] On успехе список/строка обновляются
- [ ] Ошибкand отображаются in toast

---

## Task 5.7: Стили

### Description

Стor для раздела «Administrators»: таблица, кнопки, модалки, пустое состояние. Консистентность with разделамand «Settings» and «Tools».

### Файлы

- `admin/styles.css`

### Done when

- [ ] Таблица читаема and выровнена
- [ ] Кнопкand and модалкand выглядят in едином стиле with остальной админкой
- [ ] Адаптивность (on малых экранах table not ломается or заменяется on карточкand — by согласованию)

---

## Task 5.8: Тестирование

### Manual testing (checklist)

#### Список

- [ ] On открытиand #admins list загружается
- [ ] Пустое состояние отображается прand отсутствиand записей
- [ ] Отображение Telegram ID, имени, username, даты

#### Добавление

- [ ] Модалка открывается by «+ Добавить»
- [ ] Валидация отрицательного/нулевого ID
- [ ] Успешное добавление (201) — модалка закрывается, list обновляется
- [ ] Повторное добавление того же ID — 409, toast
- [ ] Несуществующий/некорректный ID — обработка 400

#### Обновление профиля

- [ ] Кнопка «Обновить» отправляет запрос
- [ ] После успеха данные in списке обновляются

#### Delete

- [ ] Модалка подтверждения открывается with корректным именем
- [ ] Отмеon not выполняет удаление
- [ ] Подтверждение выполняет DELETE and обновляет список

### Done when

- [ ] All пункты чеклиста пройдены
- [ ] В консолand нет errors

---

## Work sequence

```
DAY 1: Каркаwith and список
├── 5.1 Контейнер and роутинг
├── 5.2 API-functions
└── 5.3 Отображение списка

DAY 2: Добавление and удаление
├── 5.4 Модалка добавления
└── 5.5 Модалка подтверждения удаления

DAY 3: Доработка and тестирование
├── 5.6 Действие «Update профиль»
├── 5.7 Стили
└── 5.8 Тестирование
```

---

## Definition of Done for Phase 5

- [ ] All tasksand 5.1–5.8 done
- [ ] Раздел «Administrators» открывается by #admins
- [ ] Список администратороin загружается and отображается
- [ ] Добавление by Telegram ID работает (включая валидацию and обработку 409)
- [ ] Delete with подтверждением работает
- [ ] Обновление профиля from Telegram работает
- [ ] Manual testing done
- [ ] В консолand нет errors

---

## Out of scope in Фазу 5

- Изменение API бэкенда (all эндпоинты уже реализованы)
- Ролand and права внутрand списка администратороin (all with одинаковымand правами)
- Unit tests для JS
- Business plugins (Phase 6)

---

## Document versioning

| Version | Date | Description |
|--------|------|----------|
| 1.0 | 2026-02-06 | First version detailed planа Фазы 5 |
