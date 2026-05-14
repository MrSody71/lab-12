def test_register_user(client):
    response = client.post("/auth/register", json={
        "email": "new@test.com",
        "username": "newuser",
        "full_name": "New User",
        "password": "secret123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.com"
    assert data["username"] == "newuser"
    assert "id" in data


def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "username": "dupuser", "full_name": "Dup", "password": "password1"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400


def test_register_password_too_short(client):
    response = client.post("/auth/register", json={
        "email": "short@test.com", "username": "shortpw", "full_name": "Short", "password": "abc",
    })
    assert response.status_code == 422


def test_register_username_too_short(client):
    response = client.post("/auth/register", json={
        "email": "xy@test.com", "username": "xy", "full_name": "XY", "password": "validpass",
    })
    assert response.status_code == 422


def test_login_success(client):
    client.post("/auth/register", json={
        "email": "a@test.com", "username": "usera", "full_name": "A", "password": "password1",
    })
    response = client.post("/auth/login", data={"username": "a@test.com", "password": "password1"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "email": "b@test.com", "username": "userb", "full_name": "B", "password": "password1",
    })
    response = client.post("/auth/login", data={"username": "b@test.com", "password": "wrongpass"})
    assert response.status_code == 401

