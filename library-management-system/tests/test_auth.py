"""
Tests for /auth/* endpoints.

Coverage
--------
- POST /auth/register  — success, duplicate email/username, validation errors
- POST /auth/login     — success, wrong password, nonexistent user
- GET  /auth/me        — authorized, deactivated, no token, invalid token
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.user import User


# ── helpers ───────────────────────────────────────────────────────────────────

def _reg(**overrides: object) -> dict:
    """Return a valid registration payload with optional field overrides."""
    return {
        "email": "new@example.com",
        "username": "newuser",
        "full_name": "New User",
        "password": "securepass123",
        **overrides,
    }


# ── registration ──────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json=_reg())
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["username"] == "newuser"
    assert data["is_admin"] is False
    assert data["is_active"] is True
    assert "id" in data
    assert "hashed_password" not in data


async def test_register_duplicate_email(
    client: AsyncClient, regular_user: User
) -> None:
    response = await client.post(
        "/auth/register",
        json=_reg(email=regular_user.email, username="otherusername"),
    )
    assert response.status_code == 400
    assert "Email" in response.json()["detail"]


async def test_register_duplicate_username(
    client: AsyncClient, regular_user: User
) -> None:
    response = await client.post(
        "/auth/register",
        json=_reg(email="unique@example.com", username=regular_user.username),
    )
    assert response.status_code == 400
    assert "Username" in response.json()["detail"]


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("password", "short"),       # 5 chars, below min_length=8
        ("password", "1234567"),     # 7 chars, still below min_length=8
        ("username", "ab"),          # 2 chars, below min_length=3
        ("email",    "not-an-email"),
    ],
    ids=["pw_5ch", "pw_7ch", "username_2ch", "bad_email"],
)
async def test_register_short_password(
    client: AsyncClient, field: str, bad_value: str
) -> None:
    """Any Pydantic validation failure must return 422."""
    response = await client.post("/auth/register", json=_reg(**{field: bad_value}))
    assert response.status_code == 422


# ── login ─────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient, regular_user: User) -> None:
    response = await client.post(
        "/auth/login",
        data={"username": regular_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


async def test_login_wrong_password(client: AsyncClient, regular_user: User) -> None:
    response = await client.post(
        "/auth/login",
        data={"username": regular_user.email, "password": "wrongpass999"},
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        data={"username": "ghost@example.com", "password": "password123"},
    )
    assert response.status_code == 401


# ── /auth/me ──────────────────────────────────────────────────────────────────

async def test_get_me_authorized(
    client: AsyncClient,
    auth_headers: dict[str, str],
    regular_user: User,
) -> None:
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == regular_user.email
    assert data["username"] == regular_user.username
    assert data["is_admin"] is False


async def test_get_me_no_token(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_get_me_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert response.status_code == 401


async def test_get_me_deactivated_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
    regular_user: User,
    db_session: Session,
) -> None:
    """A valid token for a deactivated account must be rejected (is_active fix)."""
    regular_user.is_active = False
    db_session.commit()

    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 401


# ── security: unit tests ──────────────────────────────────────────────────────

from datetime import timedelta as _td  # noqa: E402

from app.core.security import (  # noqa: E402
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    hashed = hash_password("mysecretpass")
    assert hashed != "mysecretpass"
    assert verify_password("mysecretpass", hashed) is True
    assert verify_password("wrongpass", hashed) is False


def test_create_and_decode_token() -> None:
    token = create_access_token({"sub": "42"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"


def test_decode_invalid_token() -> None:
    assert decode_token("this.is.not.valid") is None


def test_create_token_custom_expiry() -> None:
    token = create_access_token({"sub": "99"}, expires_delta=_td(hours=2))
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "99"


async def test_get_me_malformed_jwt_sub(client: AsyncClient) -> None:
    """JWT with non-integer sub hits the int() ValueError guard → 401."""
    token = create_access_token({"sub": "not-a-number"})
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


async def test_get_me_expired_token(client: AsyncClient) -> None:
    """Expired JWT is rejected by decode_token (JWTError) → 401."""
    token = create_access_token({"sub": "1"}, expires_delta=_td(seconds=-1))
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
