"""
Pytest configuration and shared fixtures.

Database strategy
-----------------
Each test function gets a fresh SQLite in-memory database.
StaticPool forces all SQLAlchemy connections to reuse a single underlying
connection, so data committed by one session (e.g. a user created by a
fixture) is visible to the session used by the overridden get_db dependency.

Async strategy
--------------
pytest.ini sets asyncio_mode = auto, so every async test/fixture is
automatically treated as an asyncio coroutine — no @pytest.mark.asyncio needed.
httpx.AsyncClient with ASGITransport drives the FastAPI ASGI app directly
without starting a real server.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Book, Borrowing, Fine, User  # noqa: F401 — registers ORM tables

TEST_DATABASE_URL = "sqlite:///:memory:"


# ---------------------------------------------------------------------------
# Infrastructure fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def engine():
    """Create a fully isolated in-memory SQLite engine for a single test."""
    _engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    """
    Synchronous DB session for direct fixture setup.

    Rolls back any uncommitted transaction after the test so teardown is clean
    even when a test leaves the session in a dirty state.
    """
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest_asyncio.fixture(scope="function")
async def client(engine) -> AsyncClient:
    """
    Async HTTP client pointed at the FastAPI ASGI app.

    Overrides the get_db dependency to use the same in-memory engine as
    db_session, so data committed by fixtures is immediately visible to the app.
    """
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = _SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def regular_user(db_session: Session) -> User:
    """Non-admin active user pre-committed to the database."""
    user = User(
        email="test@test.com",
        username="testuser",
        full_name="Test User",
        hashed_password=hash_password("password123"),
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(db_session: Session) -> User:
    """Admin active user pre-committed to the database."""
    user = User(
        email="admin@test.com",
        username="adminuser",
        full_name="Admin User",
        hashed_password=hash_password("adminpass123"),
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Auth header fixtures  (async — they POST to /auth/login)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client: AsyncClient, regular_user: User) -> dict[str, str]:
    """
    Bearer token headers for the regular user.

    Depends on both `client` (async) and `regular_user` (sync).
    pytest-asyncio handles the mixed sync/async dependency chain correctly.
    """
    response = await client.post(
        "/auth/login",
        data={"username": regular_user.email, "password": "password123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    """Bearer token headers for the admin user."""
    response = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "adminpass123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Domain object fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def sample_book(db_session: Session) -> Book:
    """A book with 3 copies committed directly to the database."""
    book = Book(
        title="The Great Gatsby",
        author="F. Scott Fitzgerald",
        isbn="9780743273565",
        genre="Fiction",
        year_published=1925,
        total_copies=3,
        available_copies=3,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


@pytest.fixture(scope="function")
def borrowed_book(db_session: Session, sample_book: Book, regular_user: User) -> Borrowing:
    """An active (not returned) borrowing for regular_user and sample_book."""
    from datetime import datetime, timedelta, timezone

    sample_book.available_copies -= 1
    borrowing = Borrowing(
        book_id=sample_book.id,
        reader_id=regular_user.id,
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db_session.add(borrowing)
    db_session.commit()
    db_session.refresh(borrowing)
    return borrowing
