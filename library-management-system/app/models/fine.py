from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database import Base


class Fine(Base):
    __tablename__ = "fines"

    id = Column(Integer, primary_key=True, index=True)
    borrowing_id = Column(Integer, ForeignKey("borrowings.id"), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    is_paid = Column(Boolean, default=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    paid_at = Column(DateTime(timezone=True), nullable=True)

    borrowing: "Borrowing" = relationship("Borrowing", back_populates="fine")
