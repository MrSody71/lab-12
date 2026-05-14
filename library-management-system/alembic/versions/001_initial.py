"""Initial schema — create all tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("isbn", sa.String(length=20), nullable=False),
        sa.Column("genre", sa.String(length=100), nullable=True),
        sa.Column("year_published", sa.Integer(), nullable=True),
        sa.Column(
            "total_copies", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "available_copies", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isbn"),
    )
    op.create_index(op.f("ix_books_id"), "books", ["id"], unique=False)
    op.create_index(op.f("ix_books_title"), "books", ["title"], unique=False)
    op.create_index(op.f("ix_books_author"), "books", ["author"], unique=False)

    op.create_table(
        "borrowings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("reader_id", sa.Integer(), nullable=False),
        sa.Column(
            "borrowed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_returned", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["reader_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_borrowings_id"), "borrowings", ["id"], unique=False)
    op.create_index(op.f("ix_borrowings_book_id"), "borrowings", ["book_id"], unique=False)
    op.create_index(
        op.f("ix_borrowings_reader_id"), "borrowings", ["reader_id"], unique=False
    )
    op.create_index(
        op.f("ix_borrowings_is_returned"), "borrowings", ["is_returned"], unique=False
    )

    op.create_table(
        "fines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("borrowing_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column(
            "is_paid", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["borrowing_id"], ["borrowings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("borrowing_id"),
    )
    op.create_index(op.f("ix_fines_id"), "fines", ["id"], unique=False)
    op.create_index(op.f("ix_fines_is_paid"), "fines", ["is_paid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fines_is_paid"), table_name="fines")
    op.drop_index(op.f("ix_fines_id"), table_name="fines")
    op.drop_table("fines")
    op.drop_index(op.f("ix_borrowings_is_returned"), table_name="borrowings")
    op.drop_index(op.f("ix_borrowings_reader_id"), table_name="borrowings")
    op.drop_index(op.f("ix_borrowings_book_id"), table_name="borrowings")
    op.drop_index(op.f("ix_borrowings_id"), table_name="borrowings")
    op.drop_table("borrowings")
    op.drop_index(op.f("ix_books_author"), table_name="books")
    op.drop_index(op.f("ix_books_title"), table_name="books")
    op.drop_index(op.f("ix_books_id"), table_name="books")
    op.drop_table("books")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
