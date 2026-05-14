from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.book import BookResponse
from app.schemas.user import UserResponse


class BorrowingCreate(BaseModel):
    book_id: int
    due_days: int = Field(default=14, ge=1, le=30)


class BorrowingResponse(BaseModel):
    id: int
    book_id: int
    reader_id: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None
    is_returned: bool

    model_config = ConfigDict(from_attributes=True)


class BorrowingWithDetails(BorrowingResponse):
    book: BookResponse
    reader: UserResponse
