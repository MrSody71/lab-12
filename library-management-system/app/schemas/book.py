from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_isbn_digits(value: str) -> str:
    digits = value.replace("-", "").replace(" ", "")
    if not digits.isdigit() or len(digits) not in (10, 13):
        raise ValueError("ISBN must contain exactly 10 or 13 digits (hyphens/spaces ignored)")
    return value


class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    genre: str | None = None
    year_published: int | None = Field(default=None, ge=1000, le=2025)
    total_copies: int = Field(default=1, ge=1)
    description: str | None = None

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str) -> str:
        return _validate_isbn_digits(v)


class BookCreate(BookBase):
    genre: str
    year_published: int = Field(ge=1000, le=2025)


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    genre: str | None = None
    year_published: int | None = Field(default=None, ge=1000, le=2025)
    total_copies: int | None = Field(default=None, ge=1)
    description: str | None = None

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        return _validate_isbn_digits(v) if v is not None else None


class BookResponse(BookBase):
    id: int
    available_copies: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookSearch(BaseModel):
    query: str | None = None
    author: str | None = None
    genre: str | None = None
    available_only: bool = False
