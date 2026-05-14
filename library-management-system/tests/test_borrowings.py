import pytest
from app.models.user import User
from app.models.book import Book
from app.core.security import hash_password


@pytest.fixture
def user_headers(client, db):
    user = User(
        email="borrower@test.com", username="borrower", full_name="Borrower",
        hashed_password=hash_password("pass1234"),
    )
    db.add(user)
    db.commit()
    resp = client.post("/auth/login", data={"username": "borrower@test.com", "password": "pass1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def available_book(db):
    book = Book(
        title="Test Book", author="Author", isbn="978-3-16-148410-0",
        total_copies=2, available_copies=2,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def test_borrow_book(client, user_headers, available_book):
    response = client.post(
        "/borrowings/", json={"book_id": available_book.id, "due_days": 14}, headers=user_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == available_book.id
    assert "reader_id" in data
    assert "due_date" in data


def test_borrow_book_default_due_days(client, user_headers, available_book):
    response = client.post(
        "/borrowings/", json={"book_id": available_book.id}, headers=user_headers,
    )
    assert response.status_code == 201
    assert response.json()["due_date"] is not None


def test_borrow_unavailable_book(client, user_headers, db):
    book = Book(title="No Copies", author="A", isbn="0142437239", total_copies=1, available_copies=0)
    db.add(book)
    db.commit()
    response = client.post("/borrowings/", json={"book_id": book.id}, headers=user_headers)
    assert response.status_code == 400


def test_borrow_same_book_twice(client, user_headers, available_book):
    """Second borrow of the same unreturned book must be rejected."""
    client.post("/borrowings/", json={"book_id": available_book.id, "due_days": 14}, headers=user_headers)
    response = client.post(
        "/borrowings/", json={"book_id": available_book.id, "due_days": 14}, headers=user_headers,
    )
    assert response.status_code == 400


def test_due_days_validation(client, user_headers, available_book):
    for invalid in (0, 31):
        response = client.post(
            "/borrowings/", json={"book_id": available_book.id, "due_days": invalid}, headers=user_headers,
        )
        assert response.status_code == 422


def test_return_book(client, user_headers, available_book):
    borrowing = client.post(
        "/borrowings/", json={"book_id": available_book.id, "due_days": 14}, headers=user_headers,
    ).json()
    response = client.post(f"/borrowings/{borrowing['id']}/return", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["is_returned"] is True


def test_list_my_borrowings(client, user_headers, available_book):
    client.post("/borrowings/", json={"book_id": available_book.id, "due_days": 7}, headers=user_headers)
    response = client.get("/borrowings/", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "book" in data[0]
    assert "reader" in data[0]
