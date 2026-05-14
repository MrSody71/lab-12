# Code Review Report — Library Management System

## Методология

Статический анализ всех файлов в папках `app/` (роутеры, сервисы, модели, схемы, core).
Проверялись пять направлений: безопасность, производительность, логические ошибки, качество кода, обработка ошибок.
Для каждой проблемы зафиксировано точное место в коде (файл + строка), описан вектор атаки или сценарий отказа, предложено и применено конкретное исправление.

---

## Найденные проблемы

### Проблема 1: Деактивированный пользователь сохраняет доступ по JWT

| Поле | Значение |
|------|----------|
| Файл | `app/core/dependencies.py`, строки 26–28 |
| Категория | Безопасность |
| Риск | **Высокий** |

**Что сгенерировал ИИ:**
```python
user = db.query(User).filter(User.id == int(raw_id)).first()
if user is None:
    raise credentials_exception
return user
```

**В чём проблема:**
Проверяется только существование пользователя, но не поле `is_active`. Если администратор деактивирует учётную запись (например, при компрометации), все выданные ранее JWT-токены остаются валидными до истечения `ACCESS_TOKEN_EXPIRE_MINUTES`. Атакующий с похищенным токеном сохраняет доступ.

**Как исправил:**
```python
user = db.query(User).filter(User.id == user_id).first()
if user is None or not user.is_active:
    raise credentials_exception
return user
```

---

### Проблема 2: `int(raw_id)` без try/except — HTTP 500 вместо 401

| Поле | Значение |
|------|----------|
| Файл | `app/core/dependencies.py`, строка 26 |
| Категория | Безопасность / Обработка ошибок |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
raw_id = payload.get("sub")
if raw_id is None:
    raise credentials_exception
user = db.query(User).filter(User.id == int(raw_id)).first()
```

**В чём проблема:**
Если JWT сформирован вручную и поле `sub` содержит не числовую строку (например, `"admin"` или `"../etc/passwd"`), вызов `int(raw_id)` выбрасывает `ValueError`. FastAPI не перехватывает его и возвращает HTTP 500 с трейсбеком — утечка внутренней информации о стеке вызовов вместо корректного 401.

**Как исправил:**
```python
try:
    user_id = int(raw_id)
except (ValueError, TypeError):
    raise credentials_exception
user = db.query(User).filter(User.id == user_id).first()
```

---

### Проблема 3: ISBN не нормализуется — обход ограничения уникальности

| Поле | Значение |
|------|----------|
| Файл | `app/schemas/book.py`, строки 5–9 |
| Категория | Безопасность / Логика |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
def _validate_isbn_digits(value: str) -> str:
    digits = value.replace("-", "").replace(" ", "")
    if not digits.isdigit() or len(digits) not in (10, 13):
        raise ValueError("ISBN must contain exactly 10 or 13 digits (hyphens/spaces ignored)")
    return value  # ← возвращает исходную строку с дефисами
```

**В чём проблема:**
Валидатор вычисляет нормализованную форму `digits`, но возвращает исходный `value`. В базу сохраняется оригинальная строка. Это позволяет создать две книги с одинаковым ISBN в разных форматах:
- `POST /books/` с `"978-3161484100"` — создаётся успешно
- `POST /books/` с `"9783161484100"` — тоже создаётся (разные строки → `UNIQUE` не срабатывает)

Поиск `GET /books/search/isbn/9783161484100` не найдёт книгу, сохранённую как `"978-3161484100"`.

**Как исправил:**
```python
    return digits  # store normalized form so uniqueness constraint works correctly
```

---

### Проблема 4: CORS-origins захардкожены — невозможна продакшн-конфигурация

| Поле | Значение |
|------|----------|
| Файл | `app/main.py`, строки 26–33; `app/core/config.py` |
| Категория | Безопасность |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**В чём проблема:**
Разрешённые origins жёстко прописаны в коде. Для смены домена в продакшне необходимо изменять исходный код — нарушение принципа «12 Factor App». При `allow_credentials=True` любой из перечисленных источников может отправлять запросы с куками/заголовками аутентификации.

**Как исправил:**
```python
# app/core/config.py
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
]

# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,  # переопределяется через .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

В `.env` продакшна достаточно указать `CORS_ORIGINS=["https://myapp.example.com"]`.

---

### Проблема 5: Гонка запросов — `available_copies` уходит в отрицательное

| Поле | Значение |
|------|----------|
| Файл | `app/routers/borrowings.py`, строки 26–29, 49 |
| Категория | Производительность / Логика |
| Риск | **Высокий** |

**Что сгенерировал ИИ:**
```python
book = db.query(Book).filter(Book.id == borrow_in.book_id).first()
if not book:
    raise HTTPException(...)
if book.available_copies < 1:
    raise HTTPException(..., detail="No copies available")
# ... проверки ...
book.available_copies -= 1
db.add(borrowing)
db.commit()
```

**В чём проблема:**
Между чтением `available_copies` и записью нет блокировки строки. При двух одновременных запросах (например, от двух браузеров):
1. Запрос A читает `available_copies = 1`, проходит проверку
2. Запрос B читает `available_copies = 1`, проходит проверку
3. Запрос A коммитит `available_copies = 0`
4. Запрос B коммитит `available_copies = -1`

Книга выдана дважды при одном экземпляре. Аналогичная проблема при двойном возврате в `return_book`.

**Как исправил:**
```python
# borrow_book — блокировка строки до конца транзакции
book = (
    db.query(Book)
    .filter(Book.id == borrow_in.book_id)
    .with_for_update()  # SELECT ... FOR UPDATE
    .first()
)

# return_book — явный fetch с блокировкой вместо lazy-load
book = db.query(Book).filter(Book.id == borrowing.book_id).with_for_update().first()
book.available_copies += 1
```

---

### Проблема 6: Lazy-load в `return_book` — скрытый лишний SELECT

| Поле | Значение |
|------|----------|
| Файл | `app/routers/borrowings.py`, строка 105 |
| Категория | Производительность |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
borrowing.is_returned = True
borrowing.returned_at = now
borrowing.book.available_copies += 1  # ← lazy-load
```

**В чём проблема:**
SQLAlchemy lazy-load: при обращении к `borrowing.book` выполняется неявный `SELECT` книги внутри транзакции. Это:
1. Дополнительный неконтролируемый запрос к БД
2. Книга не залочена — два параллельных возврата одной и той же книги могут оба прочитать `available_copies = 0`, оба прибавить 1, и записать `available_copies = 1` вместо `2`

**Как исправил:**
```python
# Явный fetch с блокировкой перед изменением
book = db.query(Book).filter(Book.id == borrowing.book_id).with_for_update().first()

now = datetime.now(timezone.utc)
borrowing.is_returned = True
borrowing.returned_at = now
book.available_copies += 1
```

---

### Проблема 7: Нет индексов на FK-колонках `Borrowing`

| Поле | Значение |
|------|----------|
| Файл | `app/models/borrowing.py`, строки 11–12, 24 |
| Категория | Производительность |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
reader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
# ...
is_returned = Column(Boolean, default=False)
```

**В чём проблема:**
PostgreSQL не создаёт индексы по внешним ключам автоматически (в отличие от MySQL). Каждый запрос вида `filter(Borrowing.reader_id == user.id)` выполняет sequential scan. При 10 000+ выдачах `GET /borrowings/`, `GET /borrowings/overdue`, `POST /borrowings/{id}/return` — все будут деградировать до full table scan. `is_returned` участвует в `WHERE` каждого запроса на активные выдачи — без индекса аналогичная проблема.

**Как исправил:**
```python
book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
reader_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
# ...
is_returned = Column(Boolean, default=False, index=True)
```

---

### Проблема 8: Нет индекса на `Fine.is_paid`

| Поле | Значение |
|------|----------|
| Файл | `app/models/fine.py`, строка 13 |
| Категория | Производительность |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
is_paid = Column(Boolean, default=False)
```

**В чём проблема:**
`is_paid` используется в `WHERE` в трёх местах: `list_unpaid_fines`, `get_reader_stats`, `get_fines_summary`. Без индекса — sequential scan по всей таблице штрафов при каждом вызове аналитики.

**Как исправил:**
```python
is_paid = Column(Boolean, default=False, index=True)
```

---

### Проблема 9: Просрочка менее 24 часов — штраф 0.0 при `returned_at > due_date`

| Поле | Значение |
|------|----------|
| Файл | `app/services/fine_calculator.py`, строки 6–8 |
| Категория | Логика |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
def calculate_fine(due_date: datetime, returned_at: datetime, fine_per_day: float) -> float:
    """Return overdue fine. Zero when returned on time."""
    if returned_at <= due_date:
        return 0.0
    overdue_days = (returned_at - due_date).days  # ← .days отбрасывает часы
    return round(overdue_days * fine_per_day, 2)
```

**В чём проблема:**
`timedelta.days` возвращает количество полных суток. Если книга просрочена на 23 часа 59 минут:
- `returned_at > due_date` → **True** (книга реально просрочена)
- `(returned_at - due_date).days` → **0**
- Штраф → **0.0**

Функция одновременно говорит «книга просрочена» и «штраф нулевой» — логическое противоречие. Читатель может пользоваться книгой почти сутки сверх срока бесплатно.

**Как исправил:**
```python
import math

def calculate_fine(due_date: datetime, returned_at: datetime, fine_per_day: float) -> float:
    """Return overdue fine; any partial day counts as a full day."""
    if returned_at <= due_date:
        return 0.0
    overdue_seconds = (returned_at - due_date).total_seconds()
    overdue_days = math.ceil(overdue_seconds / 86400)
    return round(overdue_days * fine_per_day, 2)
```

`math.ceil` гарантирует: 1 секунда просрочки = 1 день штрафа, 24 часа 1 секунда = 2 дня штрафа.

---

### Проблема 10: `update_book` допускает `total_copies < currently_borrowed`

| Поле | Значение |
|------|----------|
| Файл | `app/routers/books.py`, строки 81–84 |
| Категория | Логика |
| Риск | **Средний** |

**Что сгенерировал ИИ:**
```python
for field, value in book_in.model_dump(exclude_unset=True).items():
    setattr(book, field, value)
db.commit()
```

**В чём проблема:**
Нет проверки согласованности `total_copies` и `available_copies`. Сценарий:
- Книга: `total_copies=5`, `available_copies=2` (3 экземпляра на руках)
- Админ вызывает `PUT /books/{id}` с `{"total_copies": 1}`
- Результат: `total_copies=1`, `available_copies=2` — физически невозможное состояние
- При следующем возврате: `available_copies = 2 + 1 = 3 > total_copies = 1`

**Как исправил:**
```python
update_data = book_in.model_dump(exclude_unset=True)
if "total_copies" in update_data:
    currently_borrowed = book.total_copies - book.available_copies
    if update_data["total_copies"] < currently_borrowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot reduce total_copies below currently borrowed count"
                f" ({currently_borrowed})"
            ),
        )
for field, value in update_data.items():
    setattr(book, field, value)
```

---

### Проблема 11: Magic number `365` — неточная аппроксимация 12 месяцев

| Поле | Значение |
|------|----------|
| Файл | `app/services/analytics.py`, строка 82 |
| Категория | Качество кода |
| Риск | **Низкий** |

**Что сгенерировал ИИ:**
```python
twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
```

**В чём проблема:**
`timedelta(days=365)` некорректно аппроксимирует 12 календарных месяцев: в високосный год теряется один день статистики. Кроме того, `365` — необъяснённое магическое число без комментария о его смысле. Аналогичный паттерн встречается в `borrowing.py` (`timedelta(days=14)`) и роутерах (`limit=100`).

**Как исправил:**
```python
_STATS_LOOKBACK_DAYS = 366  # covers 12 calendar months even in leap years

# ...
twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=_STATS_LOOKBACK_DAYS)
```

`366` гарантирует покрытие любых 12 календарных месяцев независимо от наличия високосного года.

---

## Итог

| Категория | Найдено | Исправлено |
|-----------|---------|------------|
| Безопасность | 4 | 4 |
| Производительность | 4 | 4 |
| Логика | 2 | 2 |
| Качество кода | 1 | 1 |
| Обработка ошибок | 1* | 1* |
| **Итого** | **11** | **11** |

*Проблема 2 (ValueError) относится к обоим столбцам «Безопасность» и «Обработка ошибок».

### Файлы, изменённые в ходе ревью

| Файл | Проблемы |
|------|----------|
| `app/core/dependencies.py` | #1, #2 |
| `app/schemas/book.py` | #3 |
| `app/core/config.py` | #4 |
| `app/main.py` | #4 |
| `app/routers/borrowings.py` | #5, #6 |
| `app/models/borrowing.py` | #7 |
| `app/models/fine.py` | #8 |
| `app/services/fine_calculator.py` | #9 |
| `app/routers/books.py` | #10 |
| `app/services/analytics.py` | #11 |
