# Library Management System

**Автор:** Артюх Виталий Валериевич  
**Группа:** 221131  
**Вариант:** 2 — Система управления библиотекой  
**Лабораторная работа:** №12  
**Сложность:** Повышенная

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Описание проекта

**Library Management System** — REST API-сервис для автоматизации работы библиотеки, построенный на FastAPI с хранением данных в PostgreSQL. Система поддерживает полный жизненный цикл книги в библиотеке: от добавления в каталог до возврата экземпляра читателем.

Сервис реализует ролевую модель доступа: **читатели** могут просматривать каталог, брать книги и отслеживать свои выдачи, а **администраторы** управляют книгами, читателями, штрафами и просматривают аналитику. Аутентификация основана на стандарте JWT (Bearer-токены), что позволяет безопасно интегрировать API с любым фронтендом или мобильным приложением.

Встроенный модуль штрафов автоматически рассчитывает задолженность при возврате просроченной книги (10 руб. за каждый день просрочки). Административная аналитика предоставляет топ самых востребованных книг, помесячную статистику выдач за последние 12 месяцев и список должников с суммами задолженностей.

---

## Стек технологий

| Компонент            | Технология                | Версия   |
|----------------------|---------------------------|----------|
| Веб-фреймворк        | FastAPI                   | 0.111.0  |
| ASGI-сервер          | Uvicorn                   | 0.29.0   |
| ORM                  | SQLAlchemy                | 2.0.30   |
| Миграции БД          | Alembic                   | 1.13.1   |
| База данных          | PostgreSQL                | 15       |
| Валидация данных     | Pydantic v2               | 2.7.1    |
| Аутентификация       | python-jose (JWT)         | 3.3.0    |
| Хэширование паролей  | passlib (bcrypt)          | 1.7.4    |
| Тестирование         | pytest + httpx            | 8.2.0    |
| Контейнеризация      | Docker / Docker Compose   | —        |

---

## Функционал

### Аутентификация и авторизация
- Регистрация нового пользователя с валидацией email, уникального username (3–50 символов) и пароля (минимум 8 символов)
- Вход по email + пароль с получением JWT Bearer-токена
- Две роли: **читатель** (обычный пользователь) и **администратор** (`is_admin=True`)
- Защищённые эндпоинты через `Authorization: Bearer <token>`

### Управление книгами
- Полный CRUD каталога книг (только администраторы могут создавать, редактировать и удалять)
- Поиск по названию и автору (`query`), фильтрация по жанру, автору, наличию свободных экземпляров
- Поиск по ISBN (10 или 13 цифр с валидацией формата)
- Отслеживание общего (`total_copies`) и доступного (`available_copies`) количества экземпляров
- Удаление книги запрещено, если есть активные (невозвращённые) выдачи

### Выдача и возврат книг
- Читатель берёт книгу, указав количество дней (от 1 до 30, по умолчанию 14)
- Проверки при выдаче: книга существует, есть свободные экземпляры, у пользователя нет невозвращённого экземпляра этой же книги
- При возврате: фиксируется дата возврата, освобождается экземпляр
- Список всех своих выдач с детальной информацией о книге и читателе

### Автоматический расчёт штрафов
- При возврате просроченной книги автоматически создаётся запись о штрафе
- Формула: `(дата_возврата − срок_сдачи).days × FINE_PER_DAY`
- По умолчанию: **10 руб. за каждый день просрочки**
- Администратор просматривает неоплаченные штрафы и отмечает их как оплаченные

### Аналитика (только для администраторов)
- **Топ книг** — книги, отсортированные по количеству выдач
- **Помесячная статистика** — количество выдач по месяцам за последние 12 месяцев
- **Просроченные выдачи** — все активные выдачи с истёкшим сроком сдачи
- **Статистика читателя** — число выдач, текущие выдачи, сумма штрафов (общая и неоплаченная)

### Управление читателями (только для администраторов)
- Список всех читателей с пагинацией (администраторы не включаются в список)
- Просмотр профиля конкретного читателя
- История выдач читателя с детальной информацией
- Статистика активности читателя

---

## Быстрый старт (Docker Compose)

### Предварительные требования
- [Docker](https://docs.docker.com/get-docker/) ≥ 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.0

### Запуск

```bash
# 1. Клонировать репозиторий
git clone <url>
cd library-management-system

# 2. Скопировать файл переменных окружения
cp .env.example .env
# При необходимости отредактировать .env

# 3. Запустить сервисы
docker compose up --build
```

После запуска:
- API доступно по адресу: **http://localhost:8000**
- Интерактивная документация (Swagger UI): **http://localhost:8000/docs**
- ReDoc: **http://localhost:8000/redoc**

Миграции применяются автоматически при старте контейнера `app`.

### Остановка

```bash
docker compose down          # остановить контейнеры
docker compose down -v       # остановить и удалить тома (данные БД будут удалены)
```

---

## Запуск без Docker

### Требования
- Python 3.11+
- PostgreSQL 15 (запущенный локально)

### Шаги

```bash
# 1. Создать и активировать виртуальное окружение
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить переменные окружения
cp .env.example .env
# Отредактировать .env: указать DATABASE_URL с localhost вместо db
# DATABASE_URL=postgresql://library_user:library_password@localhost:5432/library_db

# 4. Применить миграции
alembic upgrade head

# 5. Запустить сервер разработки
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Переменные окружения

Все переменные задаются в файле `.env`. Шаблон находится в `.env.example`.

| Переменная                  | Описание                                              | Значение по умолчанию                                      |
|-----------------------------|-------------------------------------------------------|------------------------------------------------------------|
| `DATABASE_URL`              | URL подключения к PostgreSQL                          | `postgresql://library_user:library_password@db:5432/library_db` |
| `POSTGRES_USER`             | Пользователь PostgreSQL (для Docker)                 | `library_user`                                             |
| `POSTGRES_PASSWORD`         | Пароль PostgreSQL (для Docker)                       | `library_password`                                         |
| `POSTGRES_DB`               | Имя базы данных (для Docker)                         | `library_db`                                               |
| `SECRET_KEY`                | Секретный ключ для подписи JWT-токенов               | *(обязательно изменить в продакшене)*                      |
| `ALGORITHM`                 | Алгоритм подписи JWT                                 | `HS256`                                                    |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена в минутах                       | `30`                                                       |
| `FINE_PER_DAY`              | Штраф за один день просрочки (в рублях)              | `10.0`                                                     |

> **Важно:** Никогда не коммитьте `.env` с реальными значениями. Файл `.env` включён в `.gitignore`.

---

## API Эндпоинты

### Аутентификация `/auth`

| Метод  | Путь              | Описание                              | Авторизация    |
|--------|-------------------|---------------------------------------|----------------|
| `POST` | `/auth/register`  | Регистрация нового пользователя       | Нет            |
| `POST` | `/auth/login`     | Вход и получение JWT-токена           | Нет            |
| `GET`  | `/auth/me`        | Профиль текущего пользователя         | Читатель / Админ |

### Книги `/books`

| Метод    | Путь                        | Описание                                              | Авторизация    |
|----------|-----------------------------|-------------------------------------------------------|----------------|
| `GET`    | `/books/`                   | Список книг с фильтрами и пагинацией                 | Нет            |
| `POST`   | `/books/`                   | Добавить книгу в каталог                             | Админ          |
| `GET`    | `/books/{book_id}`          | Получить книгу по ID                                 | Нет            |
| `PUT`    | `/books/{book_id}`          | Обновить данные книги                                | Админ          |
| `DELETE` | `/books/{book_id}`          | Удалить книгу (запрещено при активных выдачах)       | Админ          |
| `GET`    | `/books/search/isbn/{isbn}` | Найти книгу по ISBN                                  | Нет            |

**Query-параметры `GET /books/`:**
- `query` — поиск по названию и автору
- `author` — фильтр по автору
- `genre` — фильтр по жанру
- `available_only=true` — только книги с доступными экземплярами
- `skip`, `limit` — пагинация (по умолчанию 0 и 100)

### Выдачи `/borrowings`

| Метод  | Путь                           | Описание                                                        | Авторизация    |
|--------|--------------------------------|-----------------------------------------------------------------|----------------|
| `POST` | `/borrowings/`                 | Взять книгу (с проверками доступности и дублей)                | Читатель / Админ |
| `GET`  | `/borrowings/`                 | Список своих выдач с деталями книги и читателя                 | Читатель / Админ |
| `POST` | `/borrowings/{id}/return`      | Вернуть книгу (автоматически рассчитывает штраф)              | Читатель / Админ |
| `GET`  | `/borrowings/overdue`          | Все просроченные выдачи                                        | Админ          |

**Тело запроса `POST /borrowings/`:**
- `book_id` (int) — ID книги
- `due_days` (int, 1–30, по умолчанию 14) — срок в днях

### Читатели `/readers`

| Метод | Путь                            | Описание                                  | Авторизация |
|-------|---------------------------------|-------------------------------------------|-------------|
| `GET` | `/readers/`                     | Список всех читателей (без администраторов) | Админ      |
| `GET` | `/readers/{reader_id}`          | Профиль конкретного читателя              | Админ       |
| `GET` | `/readers/{reader_id}/stats`    | Статистика выдач и штрафов читателя       | Админ       |
| `GET` | `/readers/{reader_id}/borrowings` | История выдач читателя с деталями       | Админ       |

### Администрирование `/admin`

| Метод  | Путь                       | Описание                                        | Авторизация |
|--------|----------------------------|-------------------------------------------------|-------------|
| `GET`  | `/admin/analytics/top-books` | Топ книг по количеству выдач                  | Админ       |
| `GET`  | `/admin/analytics/monthly`   | Выдачи по месяцам за последние 12 месяцев     | Админ       |
| `GET`  | `/admin/fines`               | Список всех неоплаченных штрафов              | Админ       |
| `POST` | `/admin/fines/{fine_id}/pay` | Отметить штраф как оплаченный                 | Админ       |

---

## Примеры запросов (curl)

### Регистрация нового пользователя

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ivan@example.com",
    "username": "ivan_petrov",
    "full_name": "Иван Петров",
    "password": "securepass123"
  }'
```

**Ответ:**
```json
{
  "id": 1,
  "email": "ivan@example.com",
  "username": "ivan_petrov",
  "full_name": "Иван Петров",
  "is_active": true,
  "is_admin": false,
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

### Вход и получение токена

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ivan@example.com&password=securepass123"
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

> Сохраните `access_token` — он понадобится для всех защищённых запросов.

---

### Получить список книг

```bash
# Все книги
curl http://localhost:8000/books/

# Поиск по ключевому слову, только доступные
curl "http://localhost:8000/books/?query=python&available_only=true"

# Фильтр по жанру с пагинацией
curl "http://localhost:8000/books/?genre=Программирование&skip=0&limit=10"
```

---

### Взять книгу

```bash
curl -X POST http://localhost:8000/borrowings/ \
  -H "Authorization: Bearer <ВАШ_ТОКЕН>" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 3,
    "due_days": 14
  }'
```

**Ответ:**
```json
{
  "id": 7,
  "book_id": 3,
  "reader_id": 1,
  "borrowed_at": "2025-01-15T10:30:00Z",
  "due_date": "2025-01-29T10:30:00Z",
  "returned_at": null,
  "is_returned": false
}
```

---

### Вернуть книгу

```bash
curl -X POST http://localhost:8000/borrowings/7/return \
  -H "Authorization: Bearer <ВАШ_ТОКЕН>"
```

**Ответ (возврат в срок — штрафа нет):**
```json
{
  "id": 7,
  "book_id": 3,
  "reader_id": 1,
  "borrowed_at": "2025-01-15T10:30:00Z",
  "due_date": "2025-01-29T10:30:00Z",
  "returned_at": "2025-01-28T14:00:00Z",
  "is_returned": true
}
```

**При возврате с просрочкой** автоматически создаётся запись о штрафе. Например, 3 дня просрочки → штраф **30.00 руб.**

---

### Посмотреть неоплаченные штрафы (admin)

```bash
curl http://localhost:8000/admin/fines \
  -H "Authorization: Bearer <ТОКЕН_АДМИНИСТРАТОРА>"
```

---

### Оплатить штраф (admin)

```bash
curl -X POST http://localhost:8000/admin/fines/5/pay \
  -H "Authorization: Bearer <ТОКЕН_АДМИНИСТРАТОРА>"
```

---

## Структура проекта

```
library-management-system/
├── app/
│   ├── core/
│   │   ├── config.py          # Настройки через pydantic-settings + get_settings()
│   │   ├── dependencies.py    # FastAPI Depends: get_current_user, get_current_admin
│   │   └── security.py        # hash_password, verify_password, create_access_token, decode_token
│   ├── models/
│   │   ├── user.py            # ORM-модель пользователя
│   │   ├── book.py            # ORM-модель книги
│   │   ├── borrowing.py       # ORM-модель выдачи
│   │   └── fine.py            # ORM-модель штрафа
│   ├── routers/
│   │   ├── auth.py            # /auth — регистрация, вход, профиль
│   │   ├── books.py           # /books — каталог книг
│   │   ├── borrowings.py      # /borrowings — выдачи и возврат
│   │   ├── readers.py         # /readers — управление читателями (admin)
│   │   └── admin.py           # /admin — аналитика и штрафы (admin)
│   ├── schemas/
│   │   ├── user.py            # UserCreate, UserResponse, Token, TokenData
│   │   ├── book.py            # BookCreate, BookUpdate, BookResponse, BookSearch
│   │   ├── borrowing.py       # BorrowingCreate, BorrowingResponse, BorrowingWithDetails
│   │   └── fine.py            # FineResponse, FineWithDetails
│   ├── services/
│   │   ├── auth.py            # AuthService: register, authenticate, create_token
│   │   ├── fine_calculator.py # calculate_fine(due_date, returned_at, fine_per_day)
│   │   └── analytics.py       # AnalyticsService: топ книг, статистика, задолженности
│   ├── database.py            # engine, SessionLocal, Base, get_db()
│   └── main.py                # FastAPI app, CORS, lifespan (create_all), роутеры
├── alembic/
│   ├── env.py                 # Конфигурация Alembic, DATABASE_URL из env
│   ├── script.py.mako         # Шаблон для генерации миграций
│   └── versions/
│       └── 001_initial.py     # Первая миграция (create_all / drop_all)
├── tests/
│   ├── conftest.py            # Фикстуры: SQLite-база, TestClient, пользователи
│   ├── test_auth.py           # Тесты регистрации и аутентификации
│   ├── test_books.py          # Тесты CRUD книг
│   ├── test_borrowings.py     # Тесты выдачи и возврата
│   └── test_readers.py        # Тесты управления читателями
├── .env                       # Переменные окружения (не коммитить!)
├── .env.example               # Шаблон переменных окружения
├── .gitignore                 # Python, .env, __pycache__, htmlcov/
├── alembic.ini                # Конфигурация Alembic
├── docker-compose.yml         # db (postgres:15) + app с healthcheck и volumes
├── Dockerfile                 # Многоэтапная сборка: builder → runtime
├── requirements.txt           # Зависимости проекта
└── prompt_log.md              # История промптов разработки
```

---

## Запуск тестов

Тесты используют SQLite in-memory базу данных и не требуют запущенного PostgreSQL.

```bash
# Активировать виртуальное окружение (если не активировано)
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

# Установить зависимости (если не установлены)
pip install -r requirements.txt

# Запустить все тесты
pytest

# Запустить с отчётом о покрытии
pytest --cov=app --cov-report=term-missing

# Запустить конкретный файл тестов
pytest tests/test_books.py -v

# Запустить тесты с подробным выводом
pytest -v
```

**Генерация HTML-отчёта о покрытии:**

```bash
pytest --cov=app --cov-report=html
# Открыть htmlcov/index.html в браузере
```

---

## Prompt Log

История промптов, использованных при разработке проекта, находится в файле [`prompt_log.md`](./library-management-system/prompt_log.md).

---

## Лицензия

MIT

---

## Об авторе

| Поле | Значение |
|------|----------|
| ФИО | Артюх Виталий Валериевич |
| Группа | 221131 |
| Вариант | 2 — Система управления библиотекой |
| Дисциплина | AI-ассистированная разработка |
| Лабораторная работа | №12 |
| Сложность: повышенная|
