def test_register_user(client):
    response = client.post("/auth/register", json={
        "email": "new@test.com",
        "full_name": "New User",
        "password": "secret123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.com"
    assert "id" in data


def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "full_name": "Dup", "password": "pass"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={"email": "a@test.com", "full_name": "A", "password": "pass"})
    response = client.post("/auth/token", data={"username": "a@test.com", "password": "pass"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "b@test.com", "full_name": "B", "password": "pass"})
    response = client.post("/auth/token", data={"username": "b@test.com", "password": "wrong"})
    assert response.status_code == 401
