from datetime import datetime, timedelta, timezone

_STATS_LOOKBACK_DAYS = 366  # covers 12 calendar months even in leap years

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.borrowing import Borrowing
from app.models.fine import Fine


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_top_books(self, limit: int = 10) -> list[dict]:
        borrow_count = func.count(Borrowing.id).label("borrow_count")
        stmt = (
            select(Book.title, Book.author, borrow_count)
            .join(Borrowing, Book.id == Borrowing.book_id)
            .group_by(Book.id, Book.title, Book.author)
            .order_by(borrow_count.desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {"title": r.title, "author": r.author, "borrow_count": r.borrow_count}
            for r in rows
        ]

    def get_overdue_borrowings(self) -> list[Borrowing]:
        now = datetime.now(timezone.utc)
        stmt = select(Borrowing).where(
            Borrowing.is_returned == False,  # noqa: E712
            Borrowing.due_date < now,
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_reader_stats(self, reader_id: int) -> dict:
        total_borrowed: int = (
            self.db.execute(
                select(func.count(Borrowing.id)).where(Borrowing.reader_id == reader_id)
            ).scalar_one()
            or 0
        )

        currently_borrowed: int = (
            self.db.execute(
                select(func.count(Borrowing.id)).where(
                    Borrowing.reader_id == reader_id,
                    Borrowing.is_returned == False,  # noqa: E712
                )
            ).scalar_one()
            or 0
        )

        total_fines: float = (
            self.db.execute(
                select(func.sum(Fine.amount))
                .join(Borrowing, Fine.borrowing_id == Borrowing.id)
                .where(Borrowing.reader_id == reader_id)
            ).scalar_one()
            or 0.0
        )

        unpaid_fines: float = (
            self.db.execute(
                select(func.sum(Fine.amount))
                .join(Borrowing, Fine.borrowing_id == Borrowing.id)
                .where(Borrowing.reader_id == reader_id, Fine.is_paid == False)  # noqa: E712
            ).scalar_one()
            or 0.0
        )

        return {
            "total_borrowed": total_borrowed,
            "currently_borrowed": currently_borrowed,
            "total_fines": round(total_fines, 2),
            "unpaid_fines": round(unpaid_fines, 2),
        }

    def get_monthly_stats(self) -> list[dict]:
        twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=_STATS_LOOKBACK_DAYS)
        year_col = extract("year", Borrowing.borrowed_at).label("year")
        month_col = extract("month", Borrowing.borrowed_at).label("month")
        stmt = (
            select(year_col, month_col, func.count(Borrowing.id).label("count"))
            .where(Borrowing.borrowed_at >= twelve_months_ago)
            .group_by(year_col, month_col)
            .order_by(year_col, month_col)
        )
        rows = self.db.execute(stmt).all()
        return [{"year": int(r.year), "month": int(r.month), "count": r.count} for r in rows]

    def get_fines_summary(self) -> dict:
        total: float = self.db.execute(select(func.sum(Fine.amount))).scalar_one() or 0.0
        paid: float = (
            self.db.execute(
                select(func.sum(Fine.amount)).where(Fine.is_paid == True)  # noqa: E712
            ).scalar_one()
            or 0.0
        )
        return {
            "total": round(total, 2),
            "paid": round(paid, 2),
            "unpaid": round(total - paid, 2),
        }
