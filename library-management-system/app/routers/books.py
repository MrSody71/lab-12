from fastapi import APIRouter, Depends, HTTPException, status
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
    """Find a book by its exact ISBN."""
    book = db.query(Book).filter(Book.isbn == isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@router.get("/", response_model=list[BookResponse])
def list_books(
    query: str | None = None,
    author: str | None = None,
    genre: str | None = None,
    available_only: bool = False,
    skip: int = 0,
    limit: int = 100,
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
    db.commit()
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
    for field, value in book_in.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    db.commit()
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
