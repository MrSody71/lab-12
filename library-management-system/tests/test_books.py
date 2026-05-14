"""
Tests for /books/* endpoints.

Coverage
--------
- GET  /books/                  — empty list, data, filters
- GET  /books/{id}              — found, not found
- GET  /books/search/isbn/{isbn}— found, not found
- POST /books/                  — admin success, user forbidden, duplicate ISBN, bad year
- PUT  /books/{id}              — admin success, field update
- DELETE /books/{id}            — no borrowings (ok), active borrowings (reject)
- Filter available_only=true
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.borrowing import Borrowing


# ── payload helpers ───────────────────────────────────────────────────────────

def _book(**overrides: object) -> dict:
    return {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "genre": "Technology",
        "year_published": 2008,
        "total_copies": 2,
        **overrides,
    }


# ── public read endpoints ─────────────────────────────────────────────────────

async def test_get_books_empty(client: AsyncClient) -> None:
    response = await client.get("/books/")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_books_with_data(client: AsyncClient, sample_book: Book) -> None:
    response = await client.get("/books/")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["id"] == sample_book.id
    assert books[0]["title"] == sample_book.title


async def test_get_book_by_id(client: AsyncClient, sample_book: Book) -> None:
    response = await client.get(f"/books/{sample_book.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_book.id
    assert data["isbn"] == sample_book.isbn


async def test_get_book_not_found(client: AsyncClient) -> None:
    response = await client.get("/books/99999")
    assert response.status_code == 404


async def test_search_by_isbn(client: AsyncClient, sample_book: Book) -> None:
    response = await client.get(f"/books/search/isbn/{sample_book.isbn}")
    assert response.status_code == 200
    assert response.json()["isbn"] == sample_book.isbn


async def test_search_invalid_isbn(client: AsyncClient) -> None:
    """Valid-format ISBN that simply doesn't exist in the DB."""
    response = await client.get("/books/search/isbn/9780000000000")
    assert response.status_code == 404


# ── admin: create ─────────────────────────────────────────────────────────────

async def test_create_book_as_admin(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post("/books/", headers=admin_headers, json=_book())
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Clean Code"
    assert data["available_copies"] == 2  # mirrors total_copies on creation
    assert "id" in data


async def test_create_book_as_user(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post("/books/", headers=auth_headers, json=_book())
    assert response.status_code == 403


async def test_create_book_duplicate_isbn(
    client: AsyncClient,
    admin_headers: dict[str, str],
    sample_book: Book,
) -> None:
    """Duplicate ISBN returns 400 (IntegrityError handled in router)."""
    response = await client.post(
        "/books/",
        headers=admin_headers,
        json=_book(isbn=sample_book.isbn),
    )
    assert response.status_code == 400
    assert "ISBN" in response.json()["detail"]


async def test_create_book_invalid_year(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    """year_published > 2025 fails Pydantic validation."""
    response = await client.post(
        "/books/", headers=admin_headers, json=_book(year_published=2030)
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "bad_isbn",
    ["123", "abcdefghij", "00000000000000"],  # wrong length / non-digits / 14-digit
    ids=["3_digits", "letters", "14_digits"],
)
async def test_create_book_invalid_isbn_format(
    client: AsyncClient, admin_headers: dict[str, str], bad_isbn: str
) -> None:
    """ISBNs that fail the digit-count check return 422."""
    response = await client.post(
        "/books/", headers=admin_headers, json=_book(isbn=bad_isbn)
    )
    assert response.status_code == 422


# ── admin: update ─────────────────────────────────────────────────────────────

async def test_update_book(
    client: AsyncClient,
    admin_headers: dict[str, str],
    sample_book: Book,
) -> None:
    response = await client.put(
        f"/books/{sample_book.id}",
        headers=admin_headers,
        json={"title": "Updated Title", "genre": "Non-Fiction"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["genre"] == "Non-Fiction"
    assert data["author"] == sample_book.author  # unchanged field


async def test_update_book_not_found(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.put(
        "/books/99999", headers=admin_headers, json={"title": "Ghost"}
    )
    assert response.status_code == 404


async def test_update_book_total_copies_below_borrowed(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: Session,
    sample_book: Book,
) -> None:
    """Cannot set total_copies < currently borrowed count."""
    from datetime import datetime, timedelta, timezone

    # Manually borrow 2 out of 3 copies
    sample_book.available_copies = 1
    for _ in range(2):
        db_session.add(
            Borrowing(
                book_id=sample_book.id,
                reader_id=1,  # placeholder; constraint not enforced in SQLite
                due_date=datetime.now(timezone.utc) + timedelta(days=14),
            )
        )
    db_session.commit()

    # Try to reduce total to 1 (< 2 borrowed) → 400
    response = await client.put(
        f"/books/{sample_book.id}",
        headers=admin_headers,
        json={"total_copies": 1},
    )
    assert response.status_code == 400
    assert "borrowed" in response.json()["detail"].lower()


# ── admin: delete ─────────────────────────────────────────────────────────────

async def test_delete_book_no_active_borrowings(
    client: AsyncClient,
    admin_headers: dict[str, str],
    sample_book: Book,
) -> None:
    response = await client.delete(
        f"/books/{sample_book.id}", headers=admin_headers
    )
    assert response.status_code == 200
    assert str(sample_book.id) in response.json()["message"]

    # Confirm it's gone
    assert (await client.get(f"/books/{sample_book.id}")).status_code == 404


async def test_delete_book_with_active_borrowings(
    client: AsyncClient,
    admin_headers: dict[str, str],
    borrowed_book: Borrowing,
) -> None:
    """Active (unreturned) borrowing blocks deletion."""
    response = await client.delete(
        f"/books/{borrowed_book.book_id}", headers=admin_headers
    )
    assert response.status_code == 400
    assert "active borrowings" in response.json()["detail"].lower()


async def test_delete_book_not_found(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.delete("/books/99999", headers=admin_headers)
    assert response.status_code == 404


# ── filter ────────────────────────────────────────────────────────────────────

async def test_filter_available_only(
    client: AsyncClient,
    sample_book: Book,
    db_session: Session,
) -> None:
    # sample_book has 3 available copies → must appear
    response = await client.get("/books/?available_only=true")
    assert response.status_code == 200
    assert any(b["id"] == sample_book.id for b in response.json())

    # Zero out copies and confirm it disappears
    sample_book.available_copies = 0
    db_session.commit()

    response = await client.get("/books/?available_only=true")
    assert response.status_code == 200
    assert not any(b["id"] == sample_book.id for b in response.json())


async def test_filter_by_author(
    client: AsyncClient, sample_book: Book
) -> None:
    response = await client.get(
        f"/books/?author={sample_book.author[:5]}"
    )
    assert response.status_code == 200
    assert any(b["id"] == sample_book.id for b in response.json())


async def test_filter_by_title_query(
    client: AsyncClient, sample_book: Book
) -> None:
    response = await client.get(
        f"/books/?query={sample_book.title[:5]}"
    )
    assert response.status_code == 200
    assert any(b["id"] == sample_book.id for b in response.json())


# ── readers endpoints ─────────────────────────────────────────────────────────

from app.models.user import User  # noqa: E402


async def test_list_readers_as_admin(
    client: AsyncClient,
    admin_headers: dict[str, str],
    regular_user: User,
) -> None:
    response = await client.get("/readers/", headers=admin_headers)
    assert response.status_code == 200
    ids = [u["id"] for u in response.json()]
    assert regular_user.id in ids


async def test_list_readers_excludes_admins(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    regular_user: User,
) -> None:
    response = await client.get("/readers/", headers=admin_headers)
    assert response.status_code == 200
    ids = [u["id"] for u in response.json()]
    assert admin_user.id not in ids
    assert regular_user.id in ids


async def test_list_readers_requires_admin(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/readers/", headers=auth_headers)
    assert response.status_code == 403


async def test_get_reader_by_id(
    client: AsyncClient,
    admin_headers: dict[str, str],
    regular_user: User,
) -> None:
    response = await client.get(f"/readers/{regular_user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == regular_user.id


async def test_get_reader_not_found(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get("/readers/99999", headers=admin_headers)
    assert response.status_code == 404


async def test_get_reader_admin_is_not_reader(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
) -> None:
    """Admin's own ID is excluded by the is_admin=False filter → 404."""
    response = await client.get(f"/readers/{admin_user.id}", headers=admin_headers)
    assert response.status_code == 404


async def test_get_reader_stats_empty(
    client: AsyncClient,
    admin_headers: dict[str, str],
    regular_user: User,
) -> None:
    response = await client.get(f"/readers/{regular_user.id}/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_borrowed"] == 0
    assert data["currently_borrowed"] == 0
    assert data["total_fines"] == 0.0
    assert data["unpaid_fines"] == 0.0


async def test_get_reader_stats_with_borrowings(
    client: AsyncClient,
    admin_headers: dict[str, str],
    borrowed_book: Borrowing,
    regular_user: User,
) -> None:
    response = await client.get(f"/readers/{regular_user.id}/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_borrowed"] == 1
    assert data["currently_borrowed"] == 1


async def test_get_reader_borrowings(
    client: AsyncClient,
    admin_headers: dict[str, str],
    borrowed_book: Borrowing,
    regular_user: User,
) -> None:
    response = await client.get(
        f"/readers/{regular_user.id}/borrowings", headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == borrowed_book.id
    assert "book" in data[0]
    assert "reader" in data[0]
