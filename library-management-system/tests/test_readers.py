"""
Tests for /readers/* endpoints (admin-only reader management).

Rewritten to use the async conftest fixtures (AsyncClient, db_session).
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User


async def test_get_me_authorized(
    client: AsyncClient,
    auth_headers: dict[str, str],
    regular_user: User,
) -> None:
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == regular_user.email


async def test_get_me_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_list_readers_forbidden_for_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/readers/", headers=auth_headers)
    assert response.status_code == 403


async def test_list_readers_as_admin(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: Session,
) -> None:
    listed = User(
        email="listed@test.com",
        username="listeduser",
        full_name="Listed",
        hashed_password=hash_password("password123"),
        is_active=True,
        is_admin=False,
    )
    db_session.add(listed)
    db_session.commit()

    response = await client.get("/readers/", headers=admin_headers)
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "listed@test.com" in emails
    assert "admin@test.com" not in emails  # admins excluded


async def test_get_reader_not_found(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get("/readers/9999", headers=admin_headers)
    assert response.status_code == 404
