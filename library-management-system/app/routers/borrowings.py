from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.borrowing import Borrowing
from app.models.book import Book
from app.models.fine import Fine
from app.schemas.borrowing import BorrowingCreate, BorrowingResponse
from app.schemas.fine import FineResponse
from app.core.dependencies import get_current_user
from app.services.fine_calculator import calculate_fine
from app.models.user import User

router = APIRouter(prefix="/borrowings", tags=["borrowings"])


@router.post("/", response_model=BorrowingResponse, status_code=status.HTTP_201_CREATED)
def borrow_book(borrow_in: BorrowingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == borrow_in.book_id, Book.is_active == True).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.available_copies < 1:
        raise HTTPException(status_code=400, detail="No copies available")
    borrowing = Borrowing(user_id=current_user.id, book_id=book.id, due_date=borrow_in.due_date)
    book.available_copies -= 1
    db.add(borrowing)
    db.commit()
    db.refresh(borrowing)
    return borrowing


@router.post("/{borrowing_id}/return", response_model=BorrowingResponse)
def return_book(borrowing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    borrowing = db.query(Borrowing).filter(Borrowing.id == borrowing_id, Borrowing.user_id == current_user.id).first()
    if not borrowing:
        raise HTTPException(status_code=404, detail="Borrowing not found")
    if borrowing.is_returned:
        raise HTTPException(status_code=400, detail="Book already returned")
    now = datetime.now(timezone.utc)
    borrowing.is_returned = True
    borrowing.returned_at = now
    borrowing.book.available_copies += 1
    fine_amount = calculate_fine(borrowing.due_date, now)
    if fine_amount > 0:
        fine = Fine(borrowing_id=borrowing.id, amount=fine_amount)
        db.add(fine)
    db.commit()
    db.refresh(borrowing)
    return borrowing


@router.get("/my", response_model=list[BorrowingResponse])
def my_borrowings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Borrowing).filter(Borrowing.user_id == current_user.id).all()


@router.get("/{borrowing_id}/fine", response_model=FineResponse)
def get_fine(borrowing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fine = db.query(Fine).join(Borrowing).filter(Fine.borrowing_id == borrowing_id, Borrowing.user_id == current_user.id).first()
    if not fine:
        raise HTTPException(status_code=404, detail="Fine not found")
    return fine
