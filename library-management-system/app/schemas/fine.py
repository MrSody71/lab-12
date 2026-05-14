from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.borrowing import BorrowingResponse


class FineResponse(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    is_paid: bool
    created_at: datetime
    paid_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class FineWithDetails(FineResponse):
    borrowing: BorrowingResponse
