from datetime import datetime, timedelta, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base


class Borrowing(Base):
    __tablename__ = "borrowings"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    reader_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    borrowed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    due_date = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=14),
    )
    returned_at = Column(DateTime(timezone=True), nullable=True)
    is_returned = Column(Boolean, default=False, index=True)

    book: "Book" = relationship("Book", back_populates="borrowings")
    reader: "User" = relationship("User", back_populates="borrowings")
    fine: "Fine" = relationship("Fine", back_populates="borrowing", uselist=False)
