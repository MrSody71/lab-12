from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.borrowing import Borrowing
from app.models.user import User
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/analytics/popular-books")
def popular_books(
    limit: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return AnalyticsService(db).get_top_books(limit)


@router.get("/analytics/overdue")
def overdue_borrowings(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    borrowings: list[Borrowing] = AnalyticsService(db).get_overdue_borrowings()
    return [
        {"id": b.id, "reader_id": b.reader_id, "book_id": b.book_id, "due_date": b.due_date}
        for b in borrowings
    ]


@router.get("/analytics/fines")
def fines_summary(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    return AnalyticsService(db).get_fines_summary()


@router.get("/analytics/monthly")
def monthly_stats(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    return AnalyticsService(db).get_monthly_stats()


@router.get("/analytics/reader/{reader_id}")
def reader_stats(
    reader_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return AnalyticsService(db).get_reader_stats(reader_id)
