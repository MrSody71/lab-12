from pydantic import BaseModel
from datetime import datetime


class BorrowingCreate(BaseModel):
    book_id: int
    due_date: datetime | None = None  # defaults to borrowed_at + 14 days via model


class BorrowingResponse(BaseModel):
    id: int
    reader_id: int
    book_id: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None
    is_returned: bool

    model_config = {"from_attributes": True}
