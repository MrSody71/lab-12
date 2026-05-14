"""Initial schema — create all tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

from app.database import Base
# Import models so that all ORM-mapped tables are registered with Base.metadata
from app.models import Book, Borrowing, Fine, User  # noqa: F401

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables defined in the ORM models."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all tables defined in the ORM models."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
