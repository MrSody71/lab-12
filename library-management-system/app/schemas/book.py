from pydantic import BaseModel
from datetime import datetime


class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    genre: str | None = None
    year_published: int | None = None
    total_copies: int = 1
    description: str | None = None


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    genre: str | None = None
    year_published: int | None = None
    total_copies: int | None = None
    description: str | None = None


class BookResponse(BookBase):
    id: int
    available_copies: int
    created_at: datetime

    model_config = {"from_attributes": True}
