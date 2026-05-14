from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.book import Book
from app.models.borrowing import Borrowing
from app.models.user import User
from app.schemas.book import BookCreate, BookResponse, BookUpdate

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/search/isbn/{isbn}", response_model=BookResponse)
def search_by_isbn(isbn: str, db: Session = Depends(get_db)) -> BookResponse:
    """Find a book by ISBN; hyphens and spaces in the path are stripped before matching."""
    normalized = isbn.replace("-", "").replace(" ", "")
    book = db.query(Book).filter(Book.isbn == normalized).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


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
    """List books with optional filters and pagination."""
    q = db.query(Book)
    if query:
        q = q.filter(Book.title.ilike(f"%{query}%") | Book.author.ilike(f"%{query}%"))
    if author:
        q = q.filter(Book.author.ilike(f"%{author}%"))
    if genre:
        q = q.filter(Book.genre.ilike(f"%{genre}%"))
    if available_only:
        q = q.filter(Book.available_copies > 0)
    return q.offset(skip).limit(limit).all()


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookResponse:
    """Retrieve a single book by its ID."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(
    book_in: BookCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> BookResponse:
    """Create a new book (admin only)."""
    data = book_in.model_dump()
    book = Book(**data, available_copies=data["total_copies"])
    db.add(book)
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


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    book_in: BookUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> BookResponse:
    """Update book fields (admin only)."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    update_data = book_in.model_dump(exclude_unset=True)
    if "total_copies" in update_data:
        currently_borrowed = book.total_copies - book.available_copies
        new_total = update_data["total_copies"]
        if new_total < currently_borrowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reduce total_copies below currently borrowed count"
                    f" ({currently_borrowed})"
                ),
            )
        # Keep available_copies consistent: adjust by the same delta as total_copies.
        update_data["available_copies"] = book.available_copies + (new_total - book.total_copies)
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


@router.delete("/{book_id}", response_model=dict)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    """Delete a book; rejected if any active borrowings exist (admin only)."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    active = (
        db.query(Borrowing)
        .filter(Borrowing.book_id == book_id, Borrowing.is_returned == False)  # noqa: E712
        .count()
    )
    if active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete book with active borrowings",
        )
    db.delete(book)
    db.commit()
    return {"message": f"Book {book_id} deleted successfully"}
