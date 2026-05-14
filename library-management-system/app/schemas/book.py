from pydantic import BaseModel
from datetime import datetime


class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    genre: str | None = None
    total_copies: int = 1


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    genre: str | None = None
    total_copies: int | None = None
    is_active: bool | None = None


class BookResponse(BookBase):
    id: int
    available_copies: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
