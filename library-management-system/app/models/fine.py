from sqlalchemy import Column, Integer, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Fine(Base):
    __tablename__ = "fines"

    id = Column(Integer, primary_key=True, index=True)
    borrowing_id = Column(Integer, ForeignKey("borrowings.id"), nullable=False, unique=True)
    amount = Column(Float, nullable=False)
    is_paid = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    borrowing = relationship("Borrowing", back_populates="fine")
