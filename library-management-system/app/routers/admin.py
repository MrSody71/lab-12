from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.services.analytics import get_most_borrowed_books, get_overdue_borrowings, get_total_fines

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/analytics/popular-books")
def popular_books(limit: int = 10, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    results = get_most_borrowed_books(db, limit)
    return [{"book": r[0].title, "author": r[0].author, "borrow_count": r[1]} for r in results]


@router.get("/analytics/overdue")
def overdue_borrowings(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    borrowings = get_overdue_borrowings(db)
    return [{"id": b.id, "reader_id": b.reader_id, "book_id": b.book_id, "due_date": b.due_date} for b in borrowings]


@router.get("/analytics/fines")
def fines_summary(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    return get_total_fines(db)
