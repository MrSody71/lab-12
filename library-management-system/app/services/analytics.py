from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.borrowing import Borrowing
from app.models.book import Book
from app.models.fine import Fine


def get_most_borrowed_books(db: Session, limit: int = 10) -> list:
    return (
        db.query(Book, func.count(Borrowing.id).label("borrow_count"))
        .join(Borrowing, Book.id == Borrowing.book_id)
        .group_by(Book.id)
        .order_by(func.count(Borrowing.id).desc())
        .limit(limit)
        .all()
    )


def get_overdue_borrowings(db: Session) -> list:
    return (
        db.query(Borrowing)
        .filter(Borrowing.is_returned == False, Borrowing.due_date < func.now())
        .all()
    )


def get_total_fines(db: Session) -> dict:
    result = db.query(
        func.sum(Fine.amount).label("total"),
        func.sum(Fine.amount).filter(Fine.is_paid == True).label("paid"),
        func.sum(Fine.amount).filter(Fine.is_paid == False).label("unpaid"),
    ).first()
    return {
        "total": result.total or 0.0,
        "paid": result.paid or 0.0,
        "unpaid": result.unpaid or 0.0,
    }
