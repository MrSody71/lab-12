from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.borrowing import Borrowing
from app.models.user import User
from app.schemas.borrowing import BorrowingWithDetails
from app.schemas.user import UserResponse
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/readers", tags=["readers"])


def _get_reader_or_404(reader_id: int, db: Session) -> User:
    reader = db.query(User).filter(User.id == reader_id, User.is_admin == False).first()  # noqa: E712
    if not reader:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")
    return reader


@router.get("/", response_model=list[UserResponse])
def list_readers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[UserResponse]:
    """List all non-admin readers with pagination (admin only)."""
    return (
        db.query(User)
        .filter(User.is_admin == False)  # noqa: E712
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{reader_id}", response_model=UserResponse)
def get_reader(
    reader_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> UserResponse:
    """Retrieve a specific reader by ID (admin only)."""
    return _get_reader_or_404(reader_id, db)


@router.get("/{reader_id}/stats", response_model=dict)
def get_reader_stats(
    reader_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    """Return borrowing and fine statistics for a reader (admin only)."""
    _get_reader_or_404(reader_id, db)
    return AnalyticsService(db).get_reader_stats(reader_id)


@router.get("/{reader_id}/borrowings", response_model=list[BorrowingWithDetails])
def get_reader_borrowings(
    reader_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[BorrowingWithDetails]:
    """Return full borrowing history for a reader (admin only)."""
    _get_reader_or_404(reader_id, db)
    return (
        db.query(Borrowing)
        .options(selectinload(Borrowing.book), selectinload(Borrowing.reader))
        .filter(Borrowing.reader_id == reader_id)
        .all()
    )
