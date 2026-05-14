import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User, Book, Borrowing, Fine  # ensure all tables are registered
from app.core.security import hash_password

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@test.com",
        username="admin",
        full_name="Admin User",
        hashed_password=hash_password("adminpass"),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db):
    user = User(
        email="user@test.com",
        username="regular_user",
        full_name="Regular User",
        hashed_password=hash_password("userpass"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(client):
    client.post("/auth/register", json={
        "email": "admin@test.com", "username": "admin", "full_name": "Admin", "password": "adminpass",
    })
    response = client.post("/auth/token", data={"username": "admin@test.com", "password": "adminpass"})
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    client.post("/auth/register", json={
        "email": "user@test.com", "username": "regular_user", "full_name": "User", "password": "userpass",
    })
    response = client.post("/auth/token", data={"username": "user@test.com", "password": "userpass"})
    return response.json()["access_token"]
