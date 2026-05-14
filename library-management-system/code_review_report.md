# Code Review Report — Library Management System
**Автор:** Артюх Виталий Валериевич  
**Группа:** 221131  
**Вариант:** 2  

## Методология
Код review проводился с помощью Claude Code (claude-sonnet-4-6).  
Анализировались файлы: `app/routers/`, `app/services/`, `app/models/`, `app/core/`, `app/schemas/`  
Критерии: безопасность, производительность, логика, стиль, обработка ошибок.

---

## Проблема 1: Деактивированный пользователь получает новый JWT-токен

### Что сгенерировал ИИ:
```python
# app/services/auth.py
def authenticate(self, email: str, password: str) -> User | None:
    user = self.db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None
```

### В чём проблема:
Метод `authenticate` выдаёт токен любому пользователю с правильным паролем, не проверяя поле `is_active`. При этом `get_current_user` в `dependencies.py` проверяет `is_active` для **существующих** токенов, но это не мешает деактивированному аккаунту получить **новый** токен сразу после блокировки.

Реальный сценарий: администратор блокирует пользователя (`is_active = False`), но тот немедленно логинится и получает свежий JWT. Токен действует весь срок `ACCESS_TOKEN_EXPIRE_MINUTES`, обходя блокировку.

### Как исправил:
```python
# app/services/auth.py
def authenticate(self, email: str, password: str) -> User | None:
    user = self.db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if user and user.is_active and verify_password(password, user.hashed_password):
        return user
    return None
```

---

## Проблема 2: Гонка при регистрации — необработанный IntegrityError → HTTP 500

### Что сгенерировал ИИ:
```python
# app/services/auth.py
def register(self, user_data: UserCreate) -> User:
    if self.db.execute(
        select(User).where(User.email == user_data.email)
    ).scalar_one_or_none():
        raise HTTPException(400, "Email already registered")
    if self.db.execute(
        select(User).where(User.username == user_data.username)
    ).scalar_one_or_none():
        raise HTTPException(400, "Username already taken")

    user = User(...)
    self.db.add(user)
    self.db.commit()   # IntegrityError здесь → неперехваченное исключение → HTTP 500
    self.db.refresh(user)
    return user
```

### В чём проблема:
Два `SELECT` перед `INSERT` создают TOCTOU-уязвимость (Time-Of-Check / Time-Of-Use). При двух одновременных запросах с одним email оба проходят проверку, оба вызывают `INSERT`, один из них получает `IntegrityError` от базы данных. Поскольку исключение не перехватывается, FastAPI возвращает HTTP 500 с трейсбеком вместо корректного HTTP 400. В production-логах это выглядит как сбой сервера.

### Как исправил:
```python
# app/services/auth.py
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username already taken",
            )
        self.db.refresh(user)
        return user
```

---

## Проблема 3: Поиск по ISBN не нормализует входные данные — дефисы дают 404

### Что сгенерировал ИИ:
```python
# app/routers/books.py
@router.get("/search/isbn/{isbn}", response_model=BookResponse)
def search_by_isbn(isbn: str, db: Session = Depends(get_db)) -> BookResponse:
    book = db.query(Book).filter(Book.isbn == isbn).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
```

### В чём проблема:
ISBN хранится в базе в нормализованном виде (только цифры, без дефисов) — это обеспечивает `field_validator` в схеме `BookCreate`. Однако при поиске по URL вида `/books/search/isbn/978-0743273565` роутер передаёт строку с дефисом напрямую в `filter`, и точное сравнение не находит запись `9780743273565`. Пользователь получает 404, хотя книга в системе есть. Это нарушение принципа наименьшего удивления: API принимает ISBN с дефисами при создании, но не принимает при поиске.

### Как исправил:
```python
# app/routers/books.py
@router.get("/search/isbn/{isbn}", response_model=BookResponse)
def search_by_isbn(isbn: str, db: Session = Depends(get_db)) -> BookResponse:
    """Find a book by ISBN; hyphens and spaces in the path are stripped before matching."""
    normalized = isbn.replace("-", "").replace(" ", "")
    book = db.query(Book).filter(Book.isbn == normalized).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book
```

---

## Проблема 4: available_copies не пересчитывается при изменении total_copies

### Что сгенерировал ИИ:
```python
# app/routers/books.py
def update_book(...):
    update_data = book_in.model_dump(exclude_unset=True)
    if "total_copies" in update_data:
        currently_borrowed = book.total_copies - book.available_copies
        if update_data["total_copies"] < currently_borrowed:
            raise HTTPException(400, "Cannot reduce total_copies below borrowed count")
    # available_copies не изменяется — дельта новых экземпляров теряется
    for field, value in update_data.items():
        setattr(book, field, value)
    db.commit()
```

### В чём проблема:
Если библиотека докупает 2 экземпляра книги и администратор обновляет `total_copies` с 3 до 5, поле `available_copies` остаётся равным 3. В системе числится 5 копий всего, но только 3 доступных — 2 физические книги «исчезают». Читатели не могут их взять, хотя книги стоят на полке. При следующем возврате borrowed-книги `available_copies` может превысить `total_copies`, сломав инварианты данных.

### Как исправил:
```python
# app/routers/books.py
    update_data = book_in.model_dump(exclude_unset=True)
    if "total_copies" in update_data:
        currently_borrowed = book.total_copies - book.available_copies
        new_total = update_data["total_copies"]
        if new_total < currently_borrowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce total_copies below currently borrowed count ({currently_borrowed})",
            )
        # Синхронизируем available_copies: прибавляем ту же дельту, что и total_copies
        update_data["available_copies"] = book.available_copies + (new_total - book.total_copies)
    for field, value in update_data.items():
        setattr(book, field, value)
```

---

## Проблема 5: Изменение ISBN на существующий → необработанный IntegrityError → HTTP 500

### Что сгенерировал ИИ:
```python
# app/routers/books.py
    for field, value in update_data.items():
        setattr(book, field, value)
    db.commit()           # IntegrityError при дублирующем ISBN → HTTP 500
    db.refresh(book)
    return book
```

### В чём проблема:
Функция `create_book` обрабатывала `IntegrityError` и возвращала HTTP 400, но `update_book` — нет. При попытке установить ISBN, уже занятый другой книгой, SQLAlchemy бросает `sqlalchemy.exc.IntegrityError`, FastAPI не перехватывает его на уровне роутера, и клиент получает HTTP 500 с внутренним трейсбеком. Это и утечка информации о внутреннем устройстве системы, и некорректный статус-код.

### Как исправил:
```python
# app/routers/books.py
    for field, value in update_data.items():
        setattr(book, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A book with this ISBN already exists",
        )
    db.refresh(book)
    return book
```

---

## Проблема 6: Неограниченный параметр limit — потенциальный DoS

### Что сгенерировал ИИ:
```python
# app/routers/books.py
@router.get("/", response_model=list[BookResponse])
def list_books(
    query: str | None = None,
    author: str | None = None,
    genre: str | None = None,
    available_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[BookResponse]:
```

### В чём проблема:
Параметры `skip` и `limit` принимаются как обычные `int` без ограничений. Любой анонимный клиент может отправить запрос `GET /books/?limit=10000000`, что вызовет полный table scan на миллионе строк, исчерпает память приложения и сделает сервис недоступным для других пользователей. Также `skip=-1` или `limit=0` привели бы к некорректному поведению SQL-запроса.

### Как исправил:
```python
# app/routers/books.py
from fastapi import APIRouter, Depends, HTTPException, Query, status

@router.get("/", response_model=list[BookResponse])
def list_books(
    query: str | None = None,
    author: str | None = None,
    genre: str | None = None,
    available_only: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[BookResponse]:
```

---

## Проблема 7: Поле year_published захардкожено le=2025 — система ломается с 1 января 2026

### Что сгенерировал ИИ:
```python
# app/schemas/book.py
class BookBase(BaseModel):
    year_published: int | None = Field(default=None, ge=1000, le=2025)

class BookCreate(BookBase):
    genre: str
    year_published: int = Field(ge=1000, le=2025)

class BookUpdate(BaseModel):
    year_published: int | None = Field(default=None, ge=1000, le=2025)
```

### В чём проблема:
Жёстко заданный верхний предел `le=2025` означает, что 1 января 2026 года ни одна новая книга не пройдёт Pydantic-валидацию при добавлении в систему. Все запросы `POST /books/` с `year_published=2026` будут возвращать HTTP 422. Ошибка не требует изменений в коде для воспроизведения — она произойдёт автоматически при смене года.

### Как исправил:
```python
# app/schemas/book.py
from datetime import datetime

_CURRENT_YEAR: int = datetime.now().year  # вычисляется один раз при старте приложения

class BookBase(BaseModel):
    year_published: int | None = Field(default=None, ge=1000, le=_CURRENT_YEAR)

class BookCreate(BookBase):
    genre: str
    year_published: int = Field(ge=1000, le=_CURRENT_YEAR)

class BookUpdate(BaseModel):
    year_published: int | None = Field(default=None, ge=1000, le=_CURRENT_YEAR)
```

---

## Итоговая таблица

| Категория | Найдено | Исправлено |
|-----------|---------|------------|
| Логические ошибки | 2 | 2 |
| Уязвимости безопасности | 2 | 2 |
| Производительность | 1 | 1 |
| Стиль кода | 1 | 1 |
| Обработка исключений | 1 | 1 |
| **Итого** | **7** | **7** |
