import pytest
from app.models.user import User
from app.core.security import hash_password


@pytest.fixture
def user_headers(client, db):
    user = User(
        email="reader@test.com", username="reader", full_name="Reader",
        hashed_password=hash_password("pass"),
    )
    db.add(user)
    db.commit()
    resp = client.post("/auth/login", data={"username": "reader@test.com", "password": "pass"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def admin_headers(client, db):
    admin = User(
        email="admin@test.com", username="admin", full_name="Admin",
        hashed_password=hash_password("adminpass"), is_admin=True,
    )
    db.add(admin)
    db.commit()
    resp = client.post("/auth/login", data={"username": "admin@test.com", "password": "adminpass"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_get_me(client, user_headers):
    """GET /auth/me returns current user."""
    response = client.get("/auth/me", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "reader@test.com"
    assert data["username"] == "reader"


def test_get_me_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_list_readers_forbidden_for_user(client, user_headers):
    response = client.get("/readers/", headers=user_headers)
    assert response.status_code == 403


def test_list_readers_as_admin(client, admin_headers, db):
    # Create a non-admin user to appear in the list.
    user = User(
        email="listed@test.com", username="listed", full_name="Listed",
        hashed_password=hash_password("pass"),
    )
    db.add(user)
    db.commit()
    response = client.get("/readers/", headers=admin_headers)
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "listed@test.com" in emails
    assert "admin@test.com" not in emails  # admins excluded


def test_get_reader_not_found(client, admin_headers):
    response = client.get("/readers/9999", headers=admin_headers)
    assert response.status_code == 404
