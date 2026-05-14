import pytest
from app.models.user import User
from app.core.security import get_password_hash


@pytest.fixture
def auth_headers(client, db):
    user = User(email="reader@test.com", full_name="Reader", hashed_password=get_password_hash("pass"))
    db.add(user)
    db.commit()
    resp = client.post("/auth/token", data={"username": "reader@test.com", "password": "pass"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_get_me(client, auth_headers):
    response = client.get("/readers/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "reader@test.com"


def test_update_me(client, auth_headers):
    response = client.patch("/readers/me", json={"full_name": "Updated Name"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


def test_get_me_unauthorized(client):
    response = client.get("/readers/me")
    assert response.status_code == 401


def test_list_readers_forbidden_for_user(client, auth_headers):
    response = client.get("/readers/", headers=auth_headers)
    assert response.status_code == 403
