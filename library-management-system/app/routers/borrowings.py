from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.dependencies import get_current_admin, get_current_user
from app.database import get_db
from app.models.book import Book
from app.models.borrowing import Borrowing
from app.models.fine import Fine
from app.models.user import User
from app.schemas.borrowing import BorrowingCreate, BorrowingResponse, BorrowingWithDetails
from app.services.fine_calculator import calculate_fine

router = APIRouter(prefix="/borrowings", tags=["borrowings"])


@router.post("/", response_model=BorrowingResponse, status_code=status.HTTP_201_CREATED)
def borrow_book(
    borrow_in: BorrowingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BorrowingResponse:
    """Borrow a book for the current user."""
    # with_for_update() locks the row until commit — prevents race condition on available_copies
    book = db.query(Book).filter(Book.id == borrow_in.book_id).with_for_update().first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.available_copies < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No copies available")

    already_borrowed = (
        db.query(Borrowing)
        .filter(
            Borrowing.reader_id == current_user.id,
            Borrowing.book_id == borrow_in.book_id,
            Borrowing.is_returned == False,  # noqa: E712
        )
        .first()
    )
    if already_borrowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an unreturned copy of this book",
        )

    due_date = datetime.now(timezone.utc) + timedelta(days=borrow_in.due_days)
    borrowing = Borrowing(reader_id=current_user.id, book_id=book.id, due_date=due_date)
    book.available_copies -= 1
    db.add(borrowing)
    db.commit()
    db.refresh(borrowing)
    return borrowing


@router.get("/overdue", response_model=list[BorrowingWithDetails])
def list_overdue(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[BorrowingWithDetails]:
    """Return all currently overdue borrowings (admin only)."""
    now = datetime.now(timezone.utc)
    return (
        db.query(Borrowing)
        .options(selectinload(Borrowing.book), selectinload(Borrowing.reader))
        .filter(Borrowing.is_returned == False, Borrowing.due_date < now)  # noqa: E712
        .all()
    )


@router.get("/", response_model=list[BorrowingWithDetails])
def list_my_borrowings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BorrowingWithDetails]:
    """Return all borrowings for the current user including book and reader details."""
    return (
        db.query(Borrowing)
        .options(selectinload(Borrowing.book), selectinload(Borrowing.reader))
        .filter(Borrowing.reader_id == current_user.id)
        .all()
    )


@router.post("/{borrowing_id}/return", response_model=BorrowingResponse)
def return_book(
    borrowing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BorrowingResponse:
    """Return a borrowed book and calculate fine if overdue."""
    borrowing = (
        db.query(Borrowing)
        .filter(Borrowing.id == borrowing_id, Borrowing.reader_id == current_user.id)
        .first()
    )
    if not borrowing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
    if borrowing.is_returned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book already returned")

    # Fetch and lock the book row explicitly — avoids lazy-load and prevents double-increment
    book = db.query(Book).filter(Book.id == borrowing.book_id).with_for_update().first()

    now = datetime.now(timezone.utc)
    borrowing.is_returned = True
    borrowing.returned_at = now
    book.available_copies += 1

    fine_amount = calculate_fine(borrowing.due_date, now, get_settings().FINE_PER_DAY)
    if fine_amount > 0:
        db.add(Fine(borrowing_id=borrowing.id, amount=fine_amount))

    db.commit()
    db.refresh(borrowing)
    return borrowing
