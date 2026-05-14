import pytest
from datetime import datetime, timedelta, timezone
from app.models.user import User
from app.models.book import Book
from app.core.security import hash_password


@pytest.fixture
def user_headers(client, db):
    user = User(email="borrower@test.com", full_name="Borrower", hashed_password=hash_password("pass"))
    db.add(user)
    db.commit()
    resp = client.post("/auth/token", data={"username": "borrower@test.com", "password": "pass"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def available_book(db):
    book = Book(title="Test Book", author="Author", isbn="999-9-99-999999-9", total_copies=2, available_copies=2)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def test_borrow_book(client, user_headers, available_book):
    due = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    response = client.post("/borrowings/", json={"book_id": available_book.id, "due_date": due}, headers=user_headers)
    assert response.status_code == 201
    assert response.json()["book_id"] == available_book.id


def test_borrow_unavailable_book(client, user_headers, db):
    book = Book(title="No Copies", author="A", isbn="000-0", total_copies=1, available_copies=0)
    db.add(book)
    db.commit()
    due = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    response = client.post("/borrowings/", json={"book_id": book.id, "due_date": due}, headers=user_headers)
    assert response.status_code == 400


def test_return_book(client, user_headers, available_book):
    due = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    borrowing = client.post("/borrowings/", json={"book_id": available_book.id, "due_date": due}, headers=user_headers).json()
    response = client.post(f"/borrowings/{borrowing['id']}/return", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["is_returned"] is True


def test_my_borrowings(client, user_headers, available_book):
    due = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    client.post("/borrowings/", json={"book_id": available_book.id, "due_date": due}, headers=user_headers)
    response = client.get("/borrowings/my", headers=user_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
