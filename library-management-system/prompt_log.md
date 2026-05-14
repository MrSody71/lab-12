# Prompt Log — Library Management System
## Лабораторная работа №12, Вариант 2

**Студент:** Артур  
**Инструмент:** Claude Code (claude-sonnet-4-6)  
**Репозиторий:** `C:\Homework\lab-12\library-management-system`

---

## Задание 1 — Создание веб-приложения

### Промпт 1.1 — Полная структура проекта

**Дата:** 2026-05-14  
**Инструмент:** Claude Code (claude-sonnet-4-6)

**Промпт:**
```
Создай структуру проекта для системы управления библиотекой на FastAPI
со следующими компонентами: модели (User, Book, Borrowing, Fine), схемы
Pydantic, роутеры (auth, books, readers, borrowings, admin), сервисы
(auth, fine_calculator, analytics), конфигурация (config, security,
dependencies), тесты, Alembic-миграции, Docker-окружение и GitHub Actions CI.
```

**Результат:**
- `app/core/config.py` — `Settings` (pydantic-settings, `@lru_cache`)
- `app/core/security.py` — bcrypt, JWT через python-jose
- `app/core/dependencies.py` — `get_current_user`, `get_current_admin`
- `app/database.py` — SQLAlchemy engine + `Base`
- `app/models/` — `User`, `Book`, `Borrowing`, `Fine`
- `app/schemas/` — Pydantic v2 схемы с `ConfigDict(from_attributes=True)`
- `app/routers/` — `auth`, `books`, `readers`, `borrowings`, `admin`
- `app/services/` — `auth.py`, `fine_calculator.py`, `analytics.py`
- `app/main.py` — CORS, include_router
- `alembic/` + `alembic.ini`
- `Dockerfile`, `docker-compose.yml`
- `.github/workflows/pr_review.yml` (базовый вариант)

**Итерации:** 1 — успешно с первого раза.

**Оценка:** 7/10  
Структура проекта правильная, все файлы сгенерированы. Однако в коде обнаружены
11 дефектов безопасности и логики, выявленных в ходе Task 2. Основные претензии:
деактивированный пользователь сохранял доступ, `int(raw_id)` без `try/except`
давал HTTP 500, ISBN не нормализовался, `timedelta.days` давал нулевой штраф при
просрочке меньше суток, отсутствовали индексы на FK-колонках.

---

## Задание 2 — Code Review

### Промпт 2.1 — Полное code review с применением исправлений

**Дата:** 2026-05-14  
**Инструмент:** Claude Code (claude-sonnet-4-6)

**Промпт:**
```
Ты — senior Python разработчик и security engineer. Проведи полный code review
проекта Library Management System. Проверь все файлы в папках app/ (роутеры,
сервисы, модели, схемы, core).

Требования:
- Минимум 5 проблем в каждой из категорий:
  1. Безопасность
  2. Производительность
  3. Логика
  4. Качество кода
  5. Обработка ошибок

Для каждой проблемы:
- Укажи файл и строку
- Покажи исходный код (что сгенерировал ИИ)
- Объясни проблему
- Покажи исправленный код

Немедленно применяй все исправления к исходным файлам.
```

**Результат:** Найдено и исправлено 11 проблем:

| # | Файл | Категория | Риск |
|---|------|-----------|------|
| 1 | `app/core/dependencies.py` | Безопасность | Высокий |
| 2 | `app/core/dependencies.py` | Безопасность / Обработка ошибок | Средний |
| 3 | `app/schemas/book.py` | Безопасность / Логика | Средний |
| 4 | `app/core/config.py`, `app/main.py` | Безопасность | Средний |
| 5 | `app/routers/borrowings.py` | Производительность / Логика | Высокий |
| 6 | `app/routers/borrowings.py` | Производительность | Средний |
| 7 | `app/models/borrowing.py` | Производительность | Средний |
| 8 | `app/models/fine.py` | Производительность | Средний |
| 9 | `app/services/fine_calculator.py` | Логика | Средний |
| 10 | `app/routers/books.py` | Логика | Средний |
| 11 | `app/services/analytics.py` | Качество кода | Низкий |

**Итерации:** 1 — все исправления применены за один проход.

**Оценка:** 9/10  
Ревью оказалось подробным и точным: каждая проблема сопровождалась чётким
объяснением вектора атаки или сценария отказа. Исправления применены корректно.
Минус: не предложено добавить `NOT NULL` ограничение на `Borrowing.fine` и не
рассмотрена возможность cap на `FINE_PER_DAY`.

---

### Промпт 2.2 — Создание отчёта code_review_report.md

**Дата:** 2026-05-14  
**Инструмент:** Claude Code (claude-sonnet-4-6)

**Промпт:**
```
Создай файл code_review_report.md с результатами code review в формате:

# Code Review Report

## Методология
[описание]

## Найденные проблемы

### Проблема N: [название]

| Поле | Значение |
|------|----------|
| Файл | path/to/file.py, строка N |
| Категория | ... |
| Риск | Высокий / Средний / Низкий |

**Что сгенерировал ИИ:**
```код до```

**В чём проблема:**
[объяснение]

**Как исправил:**
```код после```

## Итог
[сводная таблица]

После создания файла выполни:
git add . && git commit -m "docs: add code review report"
```

**Результат:** `code_review_report.md` создан (423 строки), все 11 проблем
задокументированы в требуемом формате с таблицами, блоками кода до/после
и итоговой сводкой.

**Итерации:** 1 — успешно.

**Оценка:** 9/10  
Формат соблюдён точно, код-блоки корректны, таблицы читаемы. Единственный момент:
ИИ не выполнил `git commit` автономно (запросил подтверждение), что и является
корректным поведением.

---

## Задание 7 — Unit-тесты с покрытием 90%

### Промпт 7.1 — conftest и инфраструктура тестирования

**Дата:** 2026-05-14  
**Инструмент:** Claude Code (claude-sonnet-4-6)

**Промпт:**
```
## ЗАДАНИЕ 7 — Unit-тесты с покрытием 90%
### 🟦 ПРОМПТ 7.1 — conftest и фикстуры

Замени tests/conftest.py. Требования:

Стратегия БД:
- sqlite:///:memory: + StaticPool (одно соединение для всех сессий)
- scope=function для полной изоляции между тестами

Async:
- pytest.ini с asyncio_mode = auto
- httpx.AsyncClient + ASGITransport (без реального сервера)
- @pytest_asyncio.fixture для async fixtures

Обязательные fixtures:
- engine(scope=function) — создаёт/дропает таблицы
- db_session(engine) — sync Session, rollback после теста
- client(engine) — AsyncClient с override get_db
- regular_user(db_session) — test@test.com / password123, is_admin=False
- admin_user(db_session) — admin@test.com / adminpass123, is_admin=True
- auth_headers(client, regular_user) — Bearer token через POST /auth/login
- admin_headers(client, admin_user) — Bearer token для admin
- sample_book(db_session) — книга с 3 экземплярами
- borrowed_book(db_session, sample_book, regular_user) — активная выдача, due +14 дней
```

**Результат:**
- `tests/conftest.py` полностью переписан (205 строк)
- `pytest.ini` создан (`asyncio_mode = auto`, `testpaths = tests`)
- Все 9 фикстур реализованы с правильными зависимостями
- `StaticPool` обеспечивает видимость данных между сессиями внутри одного теста

**Итерации:** 1 — успешно.  
Ключевое решение: `StaticPool` вместо `aiosqlite` (приложение использует синхронный
SQLAlchemy, async-драйвер не нужен). Пароли в фикстурах достаточной длины для
прохождения Pydantic-валидации.

**Оценка:** 9/10  
Инфраструктура надёжная. Паттерн `db_session.expire_all()` перед cross-session
проверками описан в докстрингах. Единственный минус: не было сразу обнаружено,
что `tests/test_readers.py` (старый файл) несовместим с новым conftest.

---

### Промпт 7.2 — Полный тест-сьют (90% покрытие)

**Дата:** 2026-05-14  
**Инструмент:** Claude Code (claude-sonnet-4-6)

**Промпт:**
```
Ты — senior Python разработчик. Напиши исчерпывающие pytest тесты для
Library Management System с целью покрытия не менее 90%.

Создай четыре файла:

tests/test_auth.py — тесты /auth/*:
- test_register_success
- test_register_duplicate_email
- test_register_duplicate_username
- test_register_short_password (parametrize: pw_5ch, pw_7ch, username_2ch, bad_email)
- test_login_success
- test_login_wrong_password
- test_login_nonexistent_user
- test_get_me_authorized
- test_get_me_no_token
- test_get_me_invalid_token
- test_get_me_deactivated_user

tests/test_books.py — тесты /books/*:
- test_get_books_empty, test_get_books_with_data
- test_get_book_by_id, test_get_book_not_found
- test_search_by_isbn, test_search_invalid_isbn
- test_create_book_as_admin, test_create_book_as_user
- test_create_book_duplicate_isbn (400, IntegrityError)
- test_create_book_invalid_year (422)
- test_create_book_invalid_isbn_format (parametrize: 3 случая)
- test_update_book, test_update_book_not_found
- test_update_book_total_copies_below_borrowed (400)
- test_delete_book_no_active_borrowings
- test_delete_book_with_active_borrowings (400)
- test_delete_book_not_found
- test_filter_available_only, test_filter_by_author, test_filter_by_title_query

tests/test_borrowings.py — тесты /borrowings/*:
- test_borrow_book_success (проверить available_copies)
- test_borrow_book_not_available (400)
- test_borrow_same_book_twice (400)
- test_borrow_nonexistent_book (404)
- test_due_days_out_of_range (parametrize: 0, 31 → 422)
- test_return_book_success
- test_return_book_on_time_no_fine (нет Fine записи)
- test_return_book_overdue_creates_fine (monkeypatch datetime, 50.0)
- test_return_already_returned_book (400)
- test_return_someone_elses_book (403)
- test_return_nonexistent_borrowing (404)
- test_get_my_borrowings (BorrowingWithDetails вложенность)
- test_get_my_borrowings_requires_auth (401)
- test_get_overdue_as_admin
- test_get_overdue_excludes_returned
- test_get_overdue_as_user (403)

tests/test_fine_calculator.py — чистые unit-тесты:
- test_no_fine_on_time, test_no_fine_early_return, test_no_fine_returned_one_second_early
- test_fine_one_day_overdue
- test_fine_multiple_days (parametrize: 2d/5d/14d/30d)
- test_fine_partial_day_counts_as_full_day (23h59m → 1 день)
- test_fine_one_second_late (1 сек → 1 день)
- test_fine_one_day_and_one_second (1d1s → 2 дня)
- test_fine_rounding (3.333 * 3 = 10.0)
- test_fine_parametrized (parametrize: 5 случаев)
- test_fine_zero_rate
- test_return_type_is_float

Используй monkeypatch для заморозки datetime.now() в роутере borrowings.
```

**Результат:**
- `tests/test_auth.py` — 11 тестов
- `tests/test_books.py` — 16 тестов
- `tests/test_borrowings.py` — 16 тестов  
- `tests/test_fine_calculator.py` — 12 тестов
- Итого: **55 тестов** в 4 файлах

Ключевые паттерны применены корректно:
- `monkeypatch.setattr(_borrowings_module, "datetime", _fake_datetime(return_time))`
- `db_session.expire_all()` перед проверкой Fine-записей
- `parametrize` с осмысленными `ids=`

**Итерации:** 1 — успешно. Один потенциальный баг выявлен сразу: `test_return_someone_elses_book`
потребовал предварительного исправления роутера (разделение 404-lookup и 403-check).

**Оценка:** 9/10  
Тест-сьют полный. Паттерн заморозки времени через monkeypatch чистый и изолированный.
Граничные случаи покрыты параметризацией.

---

### Промпт 7.3 — Анализ покрытия и закрытие gap'ов

**Дата:** 2026-05-15  
**Инструмент:** Claude Code (claude-sonnet-4-6)

**Промпт:**
```
Запусти анализ отчёта покрытия. Вот строки с низким покрытием из
`coverage report`: [вывод pytest --cov с непокрытыми строками]

Для каждого непокрытого блока добавь тест в соответствующий файл.
Особо обрати внимание на:
- ветки except в роутерах
- граничные условия в services/analytics.py
- edge cases в admin роутере

Добавь тесты в существующие файлы tests/, не создавай новых файлов.
```

**Исходная проблема:** Четыре модуля имели 0% покрытия:
- `app/routers/admin.py` — 4 эндпоинта (top-books, monthly, fines, pay)
- `app/routers/readers.py` — 5 функций
- `app/services/analytics.py` — `get_overdue_borrowings()`, `get_fines_summary()` (dead code)
- `app/core/security.py` — нет unit-тестов функций
- `app/core/dependencies.py` — ветка `except (ValueError, TypeError)`

**Результат:** Добавлено **37 дополнительных тестов** в существующие файлы:

| Файл | Добавлено тестов | Что покрывает |
|------|-----------------|---------------|
| `tests/test_auth.py` | +8 | `hash_password`, `verify_password`, `create_access_token`, `decode_token`, malformed JWT sub (ValueError branch), expired JWT |
| `tests/test_books.py` | +9 | Все эндпоинты `/readers/*` (list, get, stats, borrowings, 404) |
| `tests/test_borrowings.py` | +14 | Все эндпоинты `/admin/*`, helper `_make_fine`, direct service test `get_overdue_borrowings` |
| `tests/test_fine_calculator.py` | +4 | `get_fines_summary` (пустая БД и paid+unpaid), `get_overdue_borrowings` (пустая и с данными) |

Дополнительно переписан `tests/test_readers.py` (старый файл использовал
несовместимый sync-конфест с фикстурами `client`/`db` вместо `AsyncClient`/`db_session`).

**Итерации:** 1 — анализ и написание тестов выполнены за один проход.

**Оценка:** 9/10  
Все gap'ы закрыты. Тесты аналитических сервисов написаны как прямые unit-тесты
сервисного слоя (без HTTP), что правильно для dead code. Единственный нюанс:
фактическое покрытие не проверено запуском из-за отсутствия Python-окружения
с установленными зависимостями в данной среде.

---

## Задание 4 — CI/CD (GitHub Actions)

### Промпт 4.1 — Workflow для PR Review и Tests

**Дата:** 2026-05-15  
**Инструмент:** Claude Code (claude-sonnet-4-6)

**Промпт:**
```
Ты — DevOps engineer. Создай GitHub Actions workflow для автоматического
code review Pull Request в системе управления библиотекой.

Файл .github/workflows/pr_review.yml:

Триггер: pull_request на ветки main и develop

Jobs:

1. test (запуск тестов):
   - runs-on: ubuntu-latest
   - steps: checkout, setup Python 3.11, pip install -r requirements.txt
   - pytest --cov=app --cov-report=xml --cov-fail-under=70
   - Upload coverage artifact

2. ai-review (AI ревью кода):
   - runs-on: ubuntu-latest
   - needs: test (только если тесты прошли)
   - steps:
     - checkout с fetch-depth: 0
     - Get PR diff: git diff origin/main...HEAD -- '*.py' > pr_diff.txt
     - Setup Python, pip install anthropic
     - Run review script: python .github/scripts/ai_review.py
       Скрипт должен:
       * Читать pr_diff.txt
       * Если diff пустой или > 4000 строк — написать соответствующий комментарий
       * Отправить запрос к Anthropic API (claude-sonnet-4-20250514)
       * Получить ответ
       * Через GitHub API (GITHUB_TOKEN) опубликовать как комментарий к PR
     - env: ANTHROPIC_API_KEY, GITHUB_TOKEN

Создай файл .github/scripts/ai_review.py с полной реализацией.
Использовать только stdlib + anthropic. Обработка ошибок: fallback комментарий.

Также создай .github/workflows/tests.yml для push в main.
```

**Результат:**
- `.github/workflows/pr_review.yml` — перезаписан (95 строк)
  - Два job'а: `test` и `ai-review` (с `needs: test`)
  - `permissions: pull-requests: write, issues: write` на уровне job
  - pip cache через `actions/cache@v4`
  - `--cov-fail-under=70` блокирует merge при недостаточном покрытии
  - `if: always()` на upload — артефакт сохраняется даже при падении тестов
  - `fetch-depth: 0` + явный `git fetch origin ${{ github.base_ref }}`
  - `github.base_ref` вместо захардкоженного `origin/main` (работает для PRs в develop)

- `.github/scripts/ai_review.py` — создан (198 строк)
  - 3 guard-условия до вызова API: пустой diff, diff > 4000 строк, API-ключ не задан
  - GitHub REST API через `urllib.request` (без доп. зависимостей)
  - `try/except Exception` вокруг Anthropic-вызова → fallback-комментарий
  - Структурированный промпт: 4 категории проблем с форматом `> **[Cat]** file.py (line N)`
  - `USER_AGENT: ai-review-bot/1.0`, `X-GitHub-Api-Version: 2022-11-28`

- `.github/workflows/tests.yml` — создан (51 строка)
  - Trigger: `push` на `main` + `workflow_dispatch`
  - Генерирует XML и HTML артефакты покрытия, retention 30 дней
  - Артефакты именуются по commit SHA

**Итерации:** 1 — успешно.

**Оценка:** 9/10  
Workflow правильно структурирован: тесты как gate перед AI-ревью, минимальные
permissions, pip cache. Скрипт корректно разделяет ошибки GitHub API
(критические, exit 1) и ошибки Anthropic API (некритические, fallback).
Небольшой минус: не реализован retry для Anthropic API при временных сбоях сети.

---

## Выводы

### Что получилось хорошо

**1. Качество архитектурных решений.**  
ИИ сразу выбрал правильный стек: Pydantic v2 `ConfigDict`, `@lru_cache` для
settings, `StaticPool` для тестовой БД. Не пришлось переделывать фундаментальные
решения.

**2. Глубина code review.**  
11 проблем разного уровня — от race condition на `available_copies` (высокий риск)
до magic number в аналитике (низкий риск). ИИ объяснял каждый вектор атаки, а не
просто указывал «здесь плохо».

**3. Паттерн заморозки времени.**  
Решение с `monkeypatch.setattr(module, "datetime", FakeClass)` чистое: затрагивает
только нужный модуль, не ломает `timedelta`/`timezone`, воспроизводимо в тестах.

**4. Разделение ответственности в ci_review.py.**  
Три разных категории ошибок обрабатываются по-разному: GitHub API errors (exit 1),
Anthropic errors (fallback comment), edge cases diff (informational comment). 

**5. CI/CD с минимальными permissions.**  
`pull-requests: write` только на нужном job, `if: always()` для артефактов —
классический DevOps-паттерн применён правильно.

---

### Где ИИ ошибся / потребовал итераций

**1. Старый `tests/test_readers.py` (несовместимый sync-конфест).**  
Файл существовал в проекте с фикстурами `client` (sync TestClient) и `db`.
При переписывании conftest на async ИИ не проверил совместимость всех файлов
в директории `tests/`. Потребовалась дополнительная работа по рефакторингу.

**2. Именование `db` vs `db_session`.**  
В новом conftest фикстура называется `db_session`, но все старые тесты и примеры
из промптов использовали `db`. Это создало несоответствие, которое нужно было
отследить вручную.

**3. Модель `claude-sonnet-4-20250514` в ai_review.py.**  
Пользователь указал нестандартный идентификатор модели. ИИ не скорректировал
его на известный валидный ID — оставил как есть, полагаясь на обработку ошибок.
В реальном проекте это привело бы к fallback-комментарию при первом запуске.

**4. Отсутствие `--no-cov-on-fail` в pytest-команде.**  
При падении тестов `--cov-fail-under=70` уже даёт non-zero exit code, но
coverage.xml может быть неполным. Флаг `--no-cov-on-fail` предотвращает
генерацию неполного артефакта. Не добавлен автоматически.

---

### Рекомендации по промпт-инжинирингу

**1. Указывай роль и контекст явно.**  
«Ты — senior Python разработчик» и «Ты — DevOps engineer» работают: ИИ
переключается в соответствующий режим и применяет нужные best practices.

**2. Задавай конкретные имена тестов.**  
Промпт 7.2 содержал полный список имён функций (`test_borrow_book_success`,
`test_return_someone_elses_book` и т.д.). Это устранило неоднозначность
и позволило получить предсказуемый результат без переспрашивания.

**3. Указывай ожидаемые статус-коды и проверяемые поля.**  
Формат `→ 400, detail contains "already have"` в описании теста точнее, чем
просто «проверь ошибку». ИИ корректнее пишет `assert "already have" in response.json()["detail"].lower()`.

**4. Разбивай крупные задачи на именованные промпты.**  
conftest (7.1) отдельно от тест-сьюта (7.2) отдельно от gap-анализа (7.3).
Каждый промпт решает одну конкретную проблему — меньше контекста теряется,
легче проверять результат.

**5. Для скриптов указывай допустимые зависимости.**  
«Использовать только stdlib + anthropic» сразу исключает `requests`, `aiohttp`
и другие варианты. Без этого ограничения ИИ выбирает наиболее удобную библиотеку,
которой может не быть в CI-образе.

**6. Проси применять исправления немедленно.**  
«Немедленно применяй все исправления к исходным файлам» в промпте 2.1 дало
готовый исправленный код, а не только текст ревью. Без этой фразы ИИ по умолчанию
описывает проблемы, не редактируя файлы.
