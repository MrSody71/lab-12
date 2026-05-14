from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.fine import Fine
from app.models.user import User
from app.schemas.fine import FineResponse, FineWithDetails
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/analytics/top-books", response_model=list[dict])
def top_books(
    limit: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[dict]:
    """Return the most borrowed books (admin only)."""
    return AnalyticsService(db).get_top_books(limit)


@router.get("/analytics/monthly", response_model=list[dict])
def monthly_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[dict]:
    """Return borrowing counts grouped by month for the last 12 months (admin only)."""
    return AnalyticsService(db).get_monthly_stats()


@router.get("/fines", response_model=list[FineWithDetails])
def list_unpaid_fines(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[FineWithDetails]:
    """Return all unpaid fines with borrowing details (admin only)."""
    return (
        db.query(Fine)
        .options(selectinload(Fine.borrowing))
        .filter(Fine.is_paid == False)  # noqa: E712
        .all()
    )


@router.post("/fines/{fine_id}/pay", response_model=FineResponse)
def pay_fine(
    fine_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> FineResponse:
    """Mark a fine as paid (admin only)."""
    fine = db.query(Fine).filter(Fine.id == fine_id).first()
    if not fine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found")
    if fine.is_paid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fine already paid")
    fine.is_paid = True
    fine.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fine)
    return fine
