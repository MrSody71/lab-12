# Code Review Report — Library Management System
### Финальный ревью · 2026-05-15

---

## Структура проекта

| Файл | Статус | Примечание |
|------|--------|------------|
| `app/main.py` | ✅ OK | Все 5 роутеров подключены |
| `app/database.py` | ✅ Исправлен | Добавлен `pool_pre_ping`, `pool_size`, `max_overflow` |
| `app/core/config.py` | ✅ OK | |
| `app/core/security.py` | ✅ OK | |
| `app/core/dependencies.py` | ✅ OK | |
| `app/models/__init__.py` | ✅ OK | Все 4 модели экспортированы |
| `app/schemas/book.py` | ✅ Исправлен | `year_published` динамический |
| `app/schemas/user.py` | ✅ OK | |
| `app/schemas/borrowing.py` | ✅ OK | |
| `app/schemas/fine.py` | ✅ OK | |
| `app/routers/auth.py` | ✅ OK | |
| `app/routers/books.py` | ✅ Исправлен | ISBN-нормализация, `available_copies`, `IntegrityError`, лимит |
| `app/routers/borrowings.py` | ✅ OK | |
| `app/routers/readers.py` | ✅ OK | |
| `app/routers/admin.py` | ✅ OK | |
| `app/services/auth.py` | ✅ Исправлен | `is_active` при логине, IntegrityError safety net |
| `app/services/fine_calculator.py` | ✅ OK | |
| `app/services/analytics.py` | ✅ OK | |
| `alembic.ini` | ✅ OK | |
| `alembic/env.py` | ✅ OK | Читает `DATABASE_URL` из окружения |
| `alembic/versions/001_initial.py` | ⚠️ Антипаттерн | `create_all/drop_all` вместо `op` (не исправлено — требует переписать миграцию) |
| `Dockerfile` | ✅ Исправлен | Добавлен non-root пользователь |
| `docker-compose.yml` | ✅ Исправлен | Убран `--reload` и dev bind-mount |
| `docker-compose.override.yml` | ✅ Создан | Dev-настройки вынесены, добавлен в `.gitignore` |
| `.env` | ✅ OK | В `.gitignore` — не коммитится |
| `.gitignore` | ✅ Обновлён | Добавлен `docker-compose.override.yml` |
| `.github/workflows/pr_review.yml` | ✅ OK | |
| `.github/workflows/tests.yml` | ✅ OK | |
| `.github/scripts/ai_review.py` | ✅ OK | |
| `tests/conftest.py` | ✅ OK | |
| `tests/test_auth.py` | ✅ Дополнен | +1 тест: логин деактивированного |
| `tests/test_books.py` | ✅ Дополнен | +3 теста: гипенированный ISBN, delta available_copies, дублирующий ISBN |
| `tests/test_borrowings.py` | ✅ OK | |
| `tests/test_fine_calculator.py` | ✅ OK | |
| `tests/test_readers.py` | ✅ OK | |
| `pytest.ini` | ✅ OK | |
| `requirements.txt` | ✅ OK | |

---

## Найденные и исправленные проблемы

---

### Проблема 1: Деактивированный пользователь получает новый JWT-токен

**Файл:** `app/services/auth.py`, метод `authenticate`
**Категория:** Безопасность
**Риск:** Высокий

**До:**
```python
def authenticate(self, email: str, password: str) -> User | None:
    user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None
```

**После:**
```python
def authenticate(self, email: str, password: str) -> User | None:
    user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user and user.is_active and verify_password(password, user.hashed_password):
        return user
    return None
```

**Пояснение:** Проверка `is_active` в `get_current_user` защищает существующие токены, но не препятствует выдаче нового токена деактивированному аккаунту — атакующий мог получить свежий JWT сразу после деактивации.

---

### Проблема 2: TOCTOU race condition в `register` — два SELECT без атомарности

**Файл:** `app/services/auth.py`, метод `register`
**Категория:** Безопасность / Логика
**Риск:** Средний

**До:**
```python
# Два отдельных SELECT перед INSERT — нет блокировки между проверкой и записью
if self.db.execute(select(User).where(User.email == user_data.email))...:
    raise HTTPException(400, "Email already registered")
if self.db.execute(select(User).where(User.username == user_data.username))...:
    raise HTTPException(400, "Username already taken")
self.db.add(user)
self.db.commit()  # IntegrityError здесь стал бы HTTP 500
```

**После:**
```python
# Те же pre-checks для понятных сообщений об ошибке
...
self.db.add(user)
try:
    self.db.commit()
except IntegrityError:           # safety net для гонки двух одновременных регистраций
    self.db.rollback()
    raise HTTPException(400, "Email or username already taken")
```

**Пояснение:** При двух одновременных запросах с одним email оба проходили pre-check, один получал успех, второй — HTTP 500 (необработанный `IntegrityError`) вместо 400.

---

### Проблема 3: `search_by_isbn` не нормализует ISBN — дефисы в URL дают 404

**Файл:** `app/routers/books.py`, функция `search_by_isbn`
**Категория:** Логика
**Риск:** Средний

**До:**
```python
book = db.query(Book).filter(Book.isbn == isbn).first()
```

**После:**
```python
normalized = isbn.replace("-", "").replace(" ", "")
book = db.query(Book).filter(Book.isbn == normalized).first()
```

**Пояснение:** ISBN хранится нормализованным (только цифры), но поиск по URL `978-0743273565` делал точное сравнение со строкой с дефисом — книга не находилась.

---

### Проблема 4: `update_book` не корректирует `available_copies` при изменении `total_copies`

**Файл:** `app/routers/books.py`, функция `update_book`
**Категория:** Логика
**Риск:** Высокий

**До:**
```python
if update_data["total_copies"] < currently_borrowed:
    raise HTTPException(400, ...)
# available_copies не изменялся — дельта экземпляров «терялась»
for field, value in update_data.items():
    setattr(book, field, value)
```

**После:**
```python
new_total = update_data["total_copies"]
if new_total < currently_borrowed:
    raise HTTPException(400, ...)
# Синхронизируем available_copies: старое_значение + дельта
update_data["available_copies"] = book.available_copies + (new_total - book.total_copies)
for field, value in update_data.items():
    setattr(book, field, value)
```

**Пояснение:** Если библиотека докупала 2 экземпляра (`total_copies` 3→5), `available_copies` оставалось равным 3 — 2 физических книги «исчезали» из системы.

---

### Проблема 5: `update_book` — `IntegrityError` при смене ISBN → HTTP 500

**Файл:** `app/routers/books.py`, функция `update_book`
**Категория:** Логика / Качество
**Риск:** Средний

**До:**
```python
for field, value in update_data.items():
    setattr(book, field, value)
db.commit()  # IntegrityError → unhandled → HTTP 500 с трейсбеком
```

**После:**
```python
for field, value in update_data.items():
    setattr(book, field, value)
try:
    db.commit()
except IntegrityError:
    db.rollback()
    raise HTTPException(400, "A book with this ISBN already exists")
```

**Пояснение:** `create_book` уже обрабатывал `IntegrityError`, но `update_book` — нет; попытка установить уже существующий ISBN возвращала 500.

---

### Проблема 6: `list_books` принимает неограниченный `limit` — DoS через огромную выборку

**Файл:** `app/routers/books.py`, функция `list_books`
**Категория:** Производительность
**Риск:** Средний

**До:**
```python
skip: int = 0,
limit: int = 100,
```

**После:**
```python
skip: int = Query(default=0, ge=0),
limit: int = Query(default=100, ge=1, le=200),
```

**Пояснение:** Без `le=` любой пользователь мог запросить `?limit=1000000`, вызвав полный table scan и OOM-ситуацию.

---

### Проблема 7: `lifespan` вызывает `create_all` — обходит Alembic в продакшне

**Файл:** `app/main.py`, функция `lifespan`
**Категория:** Логика / DevOps
**Риск:** Высокий

**До:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    yield
```

**После:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Schema is managed by Alembic migrations (`alembic upgrade head`).
    # Never call create_all() here — it bypasses migration history and causes
    # race conditions when multiple app instances start simultaneously.
    yield
```

**Пояснение:** `create_all` при старте нескольких инстансов одновременно создаёт race condition; при наличии Alembic он должен быть единственным источником изменений схемы.

---

### Проблема 8: `year_published` захардкожен `le=2025` — блокирует добавление книг в 2026+

**Файл:** `app/schemas/book.py`
**Категория:** Логика / Качество
**Риск:** Средний

**До:**
```python
year_published: int | None = Field(default=None, ge=1000, le=2025)
```

**После:**
```python
_CURRENT_YEAR: int = datetime.now().year
...
year_published: int | None = Field(default=None, ge=1000, le=_CURRENT_YEAR)
```

**Пояснение:** Захардкоженный 2025 превратил бы систему в нерабочую с 1 января 2026 — ни одна новая книга не прошла бы валидацию.

---

### Проблема 9: Нет `pool_pre_ping` — приложение падает после перезапуска БД

**Файл:** `app/database.py`
**Категория:** Производительность / Надёжность
**Риск:** Средний

**До:**
```python
engine = create_engine(get_settings().DATABASE_URL)
```

**После:**
```python
engine = create_engine(
    get_settings().DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
```

**Пояснение:** Без `pool_pre_ping` SQLAlchemy использует соединения из пула, которые могут быть закрыты со стороны PostgreSQL (рестарт, timeout) — следующий запрос получает `OperationalError` вместо прозрачного переподключения.

---

### Проблема 10: `Dockerfile` запускает процесс от root

**Файл:** `Dockerfile`
**Категория:** DevOps / Безопасность
**Риск:** Высокий

**До:**
```dockerfile
COPY . .
EXPOSE 8000
CMD ["uvicorn", ...]
```

**После:**
```dockerfile
COPY . .

RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", ...]
```

**Пояснение:** Процесс от root внутри контейнера при успешном container-escape даёт атакующему root на хосте; минимальные привилегии — обязательный уровень защиты для продакшн-образов.

---

### Проблема 11: `docker-compose.yml` использует `--reload` и dev bind-mount в продакшне

**Файл:** `docker-compose.yml`
**Категория:** DevOps
**Риск:** Высокий

**До:**
```yaml
volumes:
  - .:/app            # перезаписывает образ хостовым кодом
command: >
  sh -c "alembic upgrade head &&
         uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

**После (`docker-compose.yml` — продакшн):**
```yaml
# volumes убран
command: >
  sh -c "alembic upgrade head &&
         uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"
```

**Dev-настройки вынесены в `docker-compose.override.yml`** (добавлен в `.gitignore`):
```yaml
services:
  app:
    volumes:
      - .:/app
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

**Пояснение:** `--reload` запускает файловый watcher (CPU overhead, security surface); bind-mount `.:/app` полностью заменяет иммутабельный образ изменяемой хост-файловой системой — нивелирует всё преимущество multi-stage build.

---

## Сводная таблица

| Категория | Найдено | Исправлено | Критических (Высоких) |
|-----------|---------|------------|----------------------|
| Безопасность | 2 | 2 | 1 |
| Производительность | 2 | 2 | 0 |
| Логика | 4 | 4 | 2 |
| Качество кода | 1 | 1 | 0 |
| Тесты | 0 | — | — |
| DevOps | 2 | 2 | 2 |
| **Итого** | **11** | **11** | **5** |

> Дополнительно выявлен антипаттерн в `alembic/versions/001_initial.py` (использует `create_all/drop_all` вместо `op.create_table`). Не исправлен в рамках этого ревью — требует полного переписывания файла миграции.

---

## Покрытие тестами

- **До ревью (оценка):** ~85% (на основе анализа кода)
- **После ревью:** ~88% (добавлено 4 новых теста на исправленную логику)
- **Непокрытые области:**
  - `alembic/` — миграции не тестируются pytest (норма, тестируются интеграционно)
  - `alembic/versions/001_initial.py` — `downgrade()` не тестируется
  - `app/main.py` — `health_check()` не покрыт тестом (тривиально, низкий приоритет)

### Добавленные тесты

| Тест | Файл | Что проверяет |
|------|------|---------------|
| `test_login_deactivated_user_is_rejected` | `test_auth.py` | `authenticate` проверяет `is_active` при логине |
| `test_search_by_isbn_with_hyphens` | `test_books.py` | Нормализация ISBN в поиске |
| `test_update_book_total_copies_increase_adjusts_available` | `test_books.py` | Корректировка `available_copies` при росте `total_copies` |
| `test_update_book_duplicate_isbn_returns_400` | `test_books.py` | `IntegrityError` при смене ISBN → 400 |
