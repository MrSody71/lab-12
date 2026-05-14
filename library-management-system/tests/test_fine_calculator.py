"""
Unit tests for app.services.fine_calculator.calculate_fine.

These tests are pure Python — no DB, no HTTP, no fixtures needed.
They validate the fine calculation logic in isolation.

Key behaviour after the math.ceil fix
--------------------------------------
- Returned exactly on time (or early)          → 0.0
- Returned any fraction of a day late          → ceil(seconds/86400) * fine_per_day
- Partial day counts as a full chargeable day
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.fine_calculator import calculate_fine

# ── constants ─────────────────────────────────────────────────────────────────

FINE_PER_DAY: float = 10.0
_BASE = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ── helpers ───────────────────────────────────────────────────────────────────

def _days(n: float) -> timedelta:
    return timedelta(seconds=int(n * 86400))


# ── no fine ───────────────────────────────────────────────────────────────────

def test_no_fine_on_time() -> None:
    """Returned exactly at the due moment → 0.0."""
    assert calculate_fine(_BASE, _BASE, FINE_PER_DAY) == 0.0


def test_no_fine_early_return() -> None:
    """Returned a week before the due date → 0.0."""
    early = _BASE - timedelta(days=7)
    assert calculate_fine(_BASE, early, FINE_PER_DAY) == 0.0


def test_no_fine_returned_one_second_early() -> None:
    assert calculate_fine(_BASE, _BASE - timedelta(seconds=1), FINE_PER_DAY) == 0.0


# ── fine: whole days ──────────────────────────────────────────────────────────

def test_fine_one_day_overdue() -> None:
    returned = _BASE + timedelta(days=1)
    assert calculate_fine(_BASE, returned, FINE_PER_DAY) == FINE_PER_DAY * 1


@pytest.mark.parametrize(
    "overdue_days,expected_fine",
    [
        (2,  20.0),
        (5,  50.0),
        (14, 140.0),
        (30, 300.0),
    ],
    ids=["2d", "5d", "14d", "30d"],
)
def test_fine_multiple_days(overdue_days: int, expected_fine: float) -> None:
    returned = _BASE + timedelta(days=overdue_days)
    assert calculate_fine(_BASE, returned, FINE_PER_DAY) == expected_fine


# ── fine: partial day → ceil ──────────────────────────────────────────────────

def test_fine_partial_day_counts_as_full_day() -> None:
    """23 hours 59 minutes late → ceil(0.999…) = 1 full day charged."""
    returned = _BASE + timedelta(hours=23, minutes=59)
    assert calculate_fine(_BASE, returned, FINE_PER_DAY) == FINE_PER_DAY * 1


def test_fine_one_second_late() -> None:
    """Even 1 second late → 1 full day charged."""
    returned = _BASE + timedelta(seconds=1)
    assert calculate_fine(_BASE, returned, FINE_PER_DAY) == FINE_PER_DAY * 1


def test_fine_one_day_and_one_second() -> None:
    """1 day + 1 second late → ceil(1.000…) = 2 days charged."""
    returned = _BASE + timedelta(days=1, seconds=1)
    assert calculate_fine(_BASE, returned, FINE_PER_DAY) == FINE_PER_DAY * 2


# ── fine: rounding ────────────────────────────────────────────────────────────

def test_fine_rounding() -> None:
    """Result is always rounded to exactly 2 decimal places."""
    returned = _BASE + timedelta(days=3)
    result = calculate_fine(_BASE, returned, fine_per_day=3.333)
    # 3 * 3.333 = 9.999 → round to 10.0
    assert result == round(result, 2)
    assert result == 10.0


@pytest.mark.parametrize(
    "fine_per_day,overdue_days,expected",
    [
        (10.0,  1,  10.0),
        (10.0,  5,  50.0),
        (7.5,   2,  15.0),
        (3.333, 3,  10.0),   # 9.999 → 10.0
        (1.005, 2,   2.01),  # banker's rounding edge: round(2.01, 2)
    ],
    ids=["10x1", "10x5", "7.5x2", "3.333x3", "1.005x2"],
)
def test_fine_parametrized(
    fine_per_day: float, overdue_days: int, expected: float
) -> None:
    returned = _BASE + timedelta(days=overdue_days)
    assert calculate_fine(_BASE, returned, fine_per_day) == expected


# ── zero fine_per_day ─────────────────────────────────────────────────────────

def test_fine_zero_rate() -> None:
    """If the library sets FINE_PER_DAY=0, no fine is ever charged."""
    returned = _BASE + timedelta(days=10)
    assert calculate_fine(_BASE, returned, fine_per_day=0.0) == 0.0


# ── return type ───────────────────────────────────────────────────────────────

def test_return_type_is_float() -> None:
    returned = _BASE + timedelta(days=1)
    result = calculate_fine(_BASE, returned, FINE_PER_DAY)
    assert isinstance(result, float)


# ── analytics service: dead-code coverage ────────────────────────────────────

from sqlalchemy.orm import Session  # noqa: E402

from app.models.book import Book  # noqa: E402
from app.models.borrowing import Borrowing  # noqa: E402
from app.models.fine import Fine  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.analytics import AnalyticsService  # noqa: E402


def test_analytics_fines_summary_empty_db(db_session: Session) -> None:
    result = AnalyticsService(db_session).get_fines_summary()
    assert result == {"total": 0.0, "paid": 0.0, "unpaid": 0.0}


def test_analytics_fines_summary_with_paid_and_unpaid(db_session: Session) -> None:
    book1 = Book(title="B1", author="A", isbn="9780000000011", genre="G",
                 year_published=2000, total_copies=2, available_copies=2)
    book2 = Book(title="B2", author="A", isbn="9780000000012", genre="G",
                 year_published=2000, total_copies=2, available_copies=2)
    user = User(email="fsummary@test.com", username="fsummary",
                hashed_password="x", is_active=True, is_admin=False)
    db_session.add_all([book1, book2, user])
    db_session.flush()

    due = datetime.now(timezone.utc) - timedelta(days=1)
    b1 = Borrowing(book_id=book1.id, reader_id=user.id, due_date=due)
    b2 = Borrowing(book_id=book2.id, reader_id=user.id, due_date=due)
    db_session.add_all([b1, b2])
    db_session.flush()

    db_session.add(Fine(borrowing_id=b1.id, amount=30.0, is_paid=True))
    db_session.add(Fine(borrowing_id=b2.id, amount=20.0, is_paid=False))
    db_session.commit()

    result = AnalyticsService(db_session).get_fines_summary()
    assert result["total"] == 50.0
    assert result["paid"] == 30.0
    assert result["unpaid"] == 20.0


def test_analytics_get_overdue_service_empty(db_session: Session) -> None:
    assert AnalyticsService(db_session).get_overdue_borrowings() == []


def test_analytics_get_overdue_service_with_data(db_session: Session) -> None:
    book = Book(title="Overdue", author="A", isbn="9780000000013", genre="G",
                year_published=2000, total_copies=1, available_copies=0)
    user = User(email="foverdue@test.com", username="foverdue",
                hashed_password="x", is_active=True, is_admin=False)
    db_session.add_all([book, user])
    db_session.flush()

    due = datetime.now(timezone.utc) - timedelta(days=3)
    borrowing = Borrowing(book_id=book.id, reader_id=user.id, due_date=due, is_returned=False)
    db_session.add(borrowing)
    db_session.commit()

    result = AnalyticsService(db_session).get_overdue_borrowings()
    assert borrowing.id in [b.id for b in result]
