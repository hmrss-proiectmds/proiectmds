"""
Integration tests for the authentication endpoints.

Tests:
  - POST /api/auth/register  (all roles)
  - POST /api/auth/login
  - GET  /api/auth/me
  - GET  /api/users/me

Requires a running PostgreSQL database (see conftest.py).
"""

import pytest

from tests.conftest import register_user, auth_headers


class TestRegister:
    async def test_register_human_player(self, http):
        user_id, username, token = await register_user(http, "human_player")
        assert user_id
        assert token

    async def test_register_ai_developer(self, http):
        _, _, token = await register_user(http, "ai_developer")
        # Verify the role is correct by checking /me
        resp = await http.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["role"] == "ai_developer"

    async def test_register_ai_agent_owner(self, http):
        _, _, token = await register_user(http, "ai_agent_owner")
        resp = await http.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["role"] == "ai_agent_owner"

    async def test_register_returns_201(self, http):
        import uuid
        uid = uuid.uuid4().hex[:10]
        resp = await http.post("/api/auth/register", json={
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "TestPass123!",
            "role": "human_player",
        })
        assert resp.status_code == 201

    async def test_register_duplicate_email_returns_409(self, http):
        import uuid
        uid = uuid.uuid4().hex[:10]
        payload = {
            "email": f"{uid}@dup.invalid",
            "username": uid,
            "password": "TestPass123!",
            "role": "human_player",
        }
        await http.post("/api/auth/register", json=payload)
        # Second register with same email
        payload2 = dict(payload)
        payload2["username"] = uid + "_b"
        resp = await http.post("/api/auth/register", json=payload2)
        assert resp.status_code == 409

    async def test_register_duplicate_username_returns_409(self, http):
        import uuid
        uid = uuid.uuid4().hex[:10]
        payload = {
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "TestPass123!",
            "role": "human_player",
        }
        await http.post("/api/auth/register", json=payload)
        payload2 = dict(payload)
        payload2["email"] = f"{uid}b@example.com"
        resp = await http.post("/api/auth/register", json=payload2)
        assert resp.status_code == 409

    async def test_register_short_password_returns_422(self, http):
        import uuid
        uid = uuid.uuid4().hex[:10]
        resp = await http.post("/api/auth/register", json={
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "short",
            "role": "human_player",
        })
        assert resp.status_code == 422

    async def test_register_invalid_role_returns_422(self, http):
        import uuid
        uid = uuid.uuid4().hex[:10]
        resp = await http.post("/api/auth/register", json={
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "TestPass123!",
            "role": "superuser",  # does not exist
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_with_valid_credentials(self, http):
        import uuid
        uid = uuid.uuid4().hex[:10]
        await http.post("/api/auth/register", json={
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "TestPass123!",
            "role": "human_player",
        })
        resp = await http.post("/api/auth/login", json={
            "email": f"{uid}@example.com",
            "password": "TestPass123!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password_returns_401(self, http):
        import uuid
        uid = uuid.uuid4().hex[:10]
        await http.post("/api/auth/register", json={
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "TestPass123!",
            "role": "human_player",
        })
        resp = await http.post("/api/auth/login", json={
            "email": f"{uid}@example.com",
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, http):
        resp = await http.post("/api/auth/login", json={
            "email": "ghost@nowhere.invalid",
            "password": "TestPass123!",
        })
        assert resp.status_code == 401


class TestMe:
    async def test_me_returns_correct_profile(self, http):
        _, username, token = await register_user(http, "ai_developer")
        resp = await http.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == username
        assert data["role"] == "ai_developer"
        assert data["elo_rating"] == 1200

    async def test_me_without_token_returns_403(self, http):
        resp = await http.get("/api/auth/me")
        assert resp.status_code in (401, 403)

    async def test_me_with_invalid_token_returns_403(self, http):
        resp = await http.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert resp.status_code in (401, 403)

    async def test_users_me_alias_works(self, http):
        _, _, token = await register_user(http, "human_player")
        resp = await http.get("/api/users/me", headers=auth_headers(token))
        assert resp.status_code == 200
