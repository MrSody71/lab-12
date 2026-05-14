import pytest
from app.models.user import User
from app.core.security import hash_password


@pytest.fixture
def admin_headers(client, db):
    user = User(
        email="adm@test.com", username="admin", full_name="Admin",
        hashed_password=hash_password("pass"), is_admin=True,
    )
    db.add(user)
    db.commit()
    resp = client.post("/auth/token", data={"username": "adm@test.com", "password": "pass"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def user_headers(client, db):
    user = User(
        email="usr@test.com", username="regularuser", full_name="User",
        hashed_password=hash_password("pass"),
    )
    db.add(user)
    db.commit()
    resp = client.post("/auth/token", data={"username": "usr@test.com", "password": "pass"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_list_books_empty(client):
    response = client.get("/books/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_book_as_admin(client, admin_headers):
    response = client.post("/books/", json={
        "title": "Clean Code",
        "author": "Robert Martin",
        "isbn": "978-0-13-235088-4",
        "genre": "Programming",
        "total_copies": 3,
    }, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Clean Code"
    assert data["available_copies"] == 3


def test_create_book_as_user_forbidden(client, user_headers):
    response = client.post("/books/", json={
        "title": "Book",
        "author": "Author",
        "isbn": "000-0-00-000000-0",
    }, headers=user_headers)
    assert response.status_code == 403


def test_get_book_not_found(client):
    response = client.get("/books/9999")
    assert response.status_code == 404


def test_update_book(client, admin_headers):
    created = client.post("/books/", json={
        "title": "Old Title",
        "author": "Author",
        "isbn": "111-1-11-111111-1",
    }, headers=admin_headers).json()
    response = client.patch(f"/books/{created['id']}", json={"title": "New Title"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


def test_delete_book(client, admin_headers):
    created = client.post("/books/", json={
        "title": "To Delete",
        "author": "Author",
        "isbn": "222-2-22-222222-2",
    }, headers=admin_headers).json()
    response = client.delete(f"/books/{created['id']}", headers=admin_headers)
    assert response.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404
