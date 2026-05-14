from pydantic import BaseModel
from datetime import datetime


class FineResponse(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    is_paid: bool
    created_at: datetime
    paid_at: datetime | None

    model_config = {"from_attributes": True}
