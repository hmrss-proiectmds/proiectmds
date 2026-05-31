"""
Shared pytest fixtures.

Database contract
-----------------
The test suite creates all tables from the ORM metadata at session start and
drops them at session end.  This requires DATABASE_URL (or TEST_DATABASE_URL)
to point at a disposable PostgreSQL database, e.g.:

  TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_platform

In CI, both DATABASE_URL and TEST_DATABASE_URL are set to the same test DB so
the FastAPI app and the test setup talk to the same schema.
"""

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app as fastapi_app

# ── DB lifecycle ──────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables at session start; drop at session end."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── HTTP client ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def http(setup_database):
    """Unauthenticated async HTTP client wired directly to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac


# ── User-creation helpers ─────────────────────────────────────────────────────


async def register_user(http: AsyncClient, role: str) -> tuple[str, str, str]:
    """
    Register a fresh user with a random username, then log in.
    Returns (user_id, username, access_token).
    """
    uid = uuid.uuid4().hex[:12]
    reg = await http.post(
        "/api/auth/register",
        json={
            "email": f"{uid}@test.invalid",
            "username": uid,
            "password": "TestPass123!",
            "role": role,
        },
    )
    assert reg.status_code == 201, f"Registration failed ({role}): {reg.text}"

    login = await http.post(
        "/api/auth/login",
        json={"email": f"{uid}@test.invalid", "password": "TestPass123!"},
    )
    assert login.status_code == 200, f"Login failed ({role}): {login.text}"

    return reg.json()["id"], uid, login.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
