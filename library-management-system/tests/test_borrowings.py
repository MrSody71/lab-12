"""
Tests for /borrowings/* endpoints.

Coverage
--------
- POST /borrowings/              — success, not available, duplicate, nonexistent book
- POST /borrowings/{id}/return   — success, on-time (no fine), overdue (fine), forbidden
- GET  /borrowings/              — list for current user
- GET  /borrowings/overdue       — admin only
- Pydantic boundary checks on due_days

Time manipulation
-----------------
monkeypatch replaces `datetime` in app.routers.borrowings so that `datetime.now()`
returns a deterministic frozen timestamp for overdue-fine assertions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

import app.routers.borrowings as _borrowings_module
from app.models.book import Book
from app.models.borrowing import Borrowing
from app.models.fine import Fine
from app.models.user import User


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_datetime(frozen: datetime):
    """Return a drop-in replacement for `datetime` that freezes `now()`."""

    class _Frozen:
        @staticmethod
        def now(tz=None) -> datetime:
            return frozen

    return _Frozen


def _make_overdue_borrowing(
    db: Session, book: Book, user: User, days_overdue: int = 5
) -> Borrowing:
    """Insert an unreturned borrowing whose due_date is already past."""
    due = datetime.now(timezone.utc) - timedelta(days=days_overdue)
    book.available_copies = max(0, book.available_copies - 1)
    b = Borrowing(book_id=book.id, reader_id=user.id, due_date=due)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


# ── borrow ────────────────────────────────────────────────────────────────────

async def test_borrow_book_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_book: Book,
    db_session: Session,
) -> None:
    response = await client.post(
        "/borrowings/",
        headers=auth_headers,
        json={"book_id": sample_book.id, "due_days": 7},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == sample_book.id
    assert data["is_returned"] is False
    assert "due_date" in data

    # available_copies must have decremented
    db_session.expire_all()
    updated = db_session.query(Book).filter_by(id=sample_book.id).first()
    assert updated.available_copies == sample_book.total_copies - 1


async def test_borrow_book_not_available(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_book: Book,
    db_session: Session,
) -> None:
    sample_book.available_copies = 0
    db_session.commit()

    response = await client.post(
        "/borrowings/",
        headers=auth_headers,
        json={"book_id": sample_book.id, "due_days": 7},
    )
    assert response.status_code == 400
    assert "No copies available" in response.json()["detail"]


async def test_borrow_same_book_twice(
    client: AsyncClient,
    auth_headers: dict[str, str],
    borrowed_book: Borrowing,
) -> None:
    """Second borrow of the same unreturned book must return 400."""
    response = await client.post(
        "/borrowings/",
        headers=auth_headers,
        json={"book_id": borrowed_book.book_id, "due_days": 7},
    )
    assert response.status_code == 400
    assert "already have" in response.json()["detail"].lower()


async def test_borrow_nonexistent_book(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/borrowings/",
        headers=auth_headers,
        json={"book_id": 99999, "due_days": 7},
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "due_days",
    [0, 31],
    ids=["test_due_days_boundary_min", "test_due_days_boundary_max"],
)
async def test_due_days_out_of_range(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_book: Book,
    due_days: int,
) -> None:
    """due_days must be in [1, 30]; values outside that range fail Pydantic (422)."""
    response = await client.post(
        "/borrowings/",
        headers=auth_headers,
        json={"book_id": sample_book.id, "due_days": due_days},
    )
    assert response.status_code == 422


# ── return ────────────────────────────────────────────────────────────────────

async def test_return_book_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
    borrowed_book: Borrowing,
) -> None:
    response = await client.post(
        f"/borrowings/{borrowed_book.id}/return",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_returned"] is True
    assert data["returned_at"] is not None


async def test_return_book_on_time_no_fine(
    client: AsyncClient,
    auth_headers: dict[str, str],
    borrowed_book: Borrowing,
    db_session: Session,
) -> None:
    """Return before due_date → calculate_fine returns 0 → no Fine row created."""
    # borrowed_book.due_date = now + 14 days, so returning now is on time
    response = await client.post(
        f"/borrowings/{borrowed_book.id}/return",
        headers=auth_headers,
    )
    assert response.status_code == 200

    db_session.expire_all()
    fine = db_session.query(Fine).filter_by(borrowing_id=borrowed_book.id).first()
    assert fine is None


async def test_return_book_overdue_creates_fine(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: Session,
    regular_user: User,
    sample_book: Book,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Return 5 days after due_date → Fine(amount=50.0) created.

    monkeypatch freezes datetime.now() inside the router at a known timestamp
    so the fine amount is deterministic regardless of wall-clock time.
    """
    due_date = datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc)
    return_time = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)  # +5 days

    # Insert overdue borrowing directly — bypasses the borrow endpoint
    sample_book.available_copies -= 1
    borrowing = Borrowing(
        book_id=sample_book.id,
        reader_id=regular_user.id,
        due_date=due_date,
    )
    db_session.add(borrowing)
    db_session.commit()
    db_session.refresh(borrowing)

    # Freeze datetime.now() in the router to return_time
    monkeypatch.setattr(_borrowings_module, "datetime", _fake_datetime(return_time))

    response = await client.post(
        f"/borrowings/{borrowing.id}/return",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_returned"] is True

    # Fine = ceil(5 days) * FINE_PER_DAY(10.0) = 50.0
    db_session.expire_all()
    fine = db_session.query(Fine).filter_by(borrowing_id=borrowing.id).first()
    assert fine is not None
    assert fine.amount == 50.0
    assert fine.is_paid is False


async def test_return_already_returned_book(
    client: AsyncClient,
    auth_headers: dict[str, str],
    borrowed_book: Borrowing,
) -> None:
    """Returning an already-returned borrowing must return 400."""
    await client.post(
        f"/borrowings/{borrowed_book.id}/return", headers=auth_headers
    )
    response = await client.post(
        f"/borrowings/{borrowed_book.id}/return", headers=auth_headers
    )
    assert response.status_code == 400
    assert "already returned" in response.json()["detail"].lower()


async def test_return_someone_elses_book(
    client: AsyncClient,
    admin_headers: dict[str, str],
    borrowed_book: Borrowing,
) -> None:
    """admin_user tries to return regular_user's borrowing → 403."""
    response = await client.post(
        f"/borrowings/{borrowed_book.id}/return",
        headers=admin_headers,
    )
    assert response.status_code == 403
    assert "Not your borrowing" in response.json()["detail"]


async def test_return_nonexistent_borrowing(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/borrowings/99999/return", headers=auth_headers
    )
    assert response.status_code == 404


# ── list ──────────────────────────────────────────────────────────────────────

async def test_get_my_borrowings(
    client: AsyncClient,
    auth_headers: dict[str, str],
    borrowed_book: Borrowing,
) -> None:
    response = await client.get("/borrowings/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    entry = data[0]
    assert entry["id"] == borrowed_book.id
    assert "book" in entry   # BorrowingWithDetails nesting
    assert "reader" in entry


async def test_get_my_borrowings_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/borrowings/")
    assert response.status_code == 401


# ── overdue (admin) ───────────────────────────────────────────────────────────

async def test_get_overdue_as_admin(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: Session,
    sample_book: Book,
    regular_user: User,
) -> None:
    overdue = _make_overdue_borrowing(db_session, sample_book, regular_user, days_overdue=3)

    response = await client.get("/borrowings/overdue", headers=admin_headers)
    assert response.status_code == 200
    ids = [b["id"] for b in response.json()]
    assert overdue.id in ids


async def test_get_overdue_excludes_returned(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: Session,
    sample_book: Book,
    regular_user: User,
) -> None:
    """A returned borrowing (even past-due) must not appear in the overdue list."""
    overdue = _make_overdue_borrowing(db_session, sample_book, regular_user, days_overdue=3)
    overdue.is_returned = True
    overdue.returned_at = datetime.now(timezone.utc)
    db_session.commit()

    response = await client.get("/borrowings/overdue", headers=admin_headers)
    assert response.status_code == 200
    ids = [b["id"] for b in response.json()]
    assert overdue.id not in ids


async def test_get_overdue_as_user(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Non-admin access to the overdue list returns 403."""
    response = await client.get("/borrowings/overdue", headers=auth_headers)
    assert response.status_code == 403
