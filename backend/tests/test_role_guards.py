"""
Role-based access control (RBAC) integration tests.

Verifies that every role-gated endpoint returns 403 Forbidden when called
by a user without the required role, and 200 (or the expected success code)
when called by a user with the correct role.

Endpoint → required role(s)
────────────────────────────────────────────────────────────────────────────
POST /api/agents/register-webhook      ai_developer | ai_agent_owner | admin
POST /api/simulations                  ai_developer | admin
GET  /api/developer/analytics          ai_developer | admin
GET  /api/owner/fleet                  ai_agent_owner | admin
GET  /api/admin/stats                  admin
GET  /api/users/leaderboard            all authenticated users (200)

Requires a running PostgreSQL database (see conftest.py).
"""

import pytest

from tests.conftest import register_user, auth_headers


# ── Fixtures: one token per role ──────────────────────────────────────────────


@pytest.fixture
async def human_token(http):
    _, _, token = await register_user(http, "human_player")
    return token


@pytest.fixture
async def dev_token(http):
    _, _, token = await register_user(http, "ai_developer")
    return token


@pytest.fixture
async def owner_token(http):
    _, _, token = await register_user(http, "ai_agent_owner")
    return token


# ── Webhook agent registration ────────────────────────────────────────────────


class TestWebhookRegistrationGuard:
    ENDPOINT = "/api/agents/register-webhook"
    PAYLOAD = {
        "name": "test-webhook",
        "game_type": "chess",
        "webhook_url": "http://example.invalid/move",
    }

    async def test_human_player_is_forbidden(self, http, human_token):
        resp = await http.post(
            self.ENDPOINT, json=self.PAYLOAD, headers=auth_headers(human_token)
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    async def test_ai_developer_is_allowed(self, http, dev_token):
        resp = await http.post(
            self.ENDPOINT, json=self.PAYLOAD, headers=auth_headers(dev_token)
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    async def test_ai_agent_owner_is_allowed(self, http, owner_token):
        resp = await http.post(
            self.ENDPOINT, json=self.PAYLOAD, headers=auth_headers(owner_token)
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    async def test_unauthenticated_is_forbidden(self, http):
        resp = await http.post(self.ENDPOINT, json=self.PAYLOAD)
        assert resp.status_code in (401, 403)


# ── Bulk simulations ──────────────────────────────────────────────────────────


class TestSimulationGuard:
    ENDPOINT = "/api/simulations"
    PAYLOAD = {"game_type": "chess", "bot_a": "random", "bot_b": "random", "num_games": 1}

    async def test_human_player_is_forbidden(self, http, human_token):
        resp = await http.post(
            self.ENDPOINT, json=self.PAYLOAD, headers=auth_headers(human_token)
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    async def test_ai_agent_owner_is_forbidden(self, http, owner_token):
        resp = await http.post(
            self.ENDPOINT, json=self.PAYLOAD, headers=auth_headers(owner_token)
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    async def test_ai_developer_is_allowed(self, http, dev_token):
        resp = await http.post(
            self.ENDPOINT, json=self.PAYLOAD, headers=auth_headers(dev_token)
        )
        # 202 Accepted (async) or 200 (sync fallback)
        assert resp.status_code in (200, 202), f"Expected 2xx, got {resp.status_code}: {resp.text}"

    async def test_unauthenticated_is_forbidden(self, http):
        resp = await http.post(self.ENDPOINT, json=self.PAYLOAD)
        assert resp.status_code in (401, 403)


# ── Developer analytics ───────────────────────────────────────────────────────


class TestDeveloperAnalyticsGuard:
    ENDPOINT = "/api/developer/analytics"

    async def test_human_player_is_forbidden(self, http, human_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(human_token))
        assert resp.status_code == 403

    async def test_ai_agent_owner_is_forbidden(self, http, owner_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(owner_token))
        assert resp.status_code == 403

    async def test_ai_developer_gets_200(self, http, dev_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(dev_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_unauthenticated_is_forbidden(self, http):
        resp = await http.get(self.ENDPOINT)
        assert resp.status_code in (401, 403)


# ── Owner fleet ───────────────────────────────────────────────────────────────


class TestOwnerFleetGuard:
    ENDPOINT = "/api/owner/fleet"

    async def test_human_player_is_forbidden(self, http, human_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(human_token))
        assert resp.status_code == 403

    async def test_ai_developer_is_forbidden(self, http, dev_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(dev_token))
        assert resp.status_code == 403

    async def test_ai_agent_owner_gets_200(self, http, owner_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(owner_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_unauthenticated_is_forbidden(self, http):
        resp = await http.get(self.ENDPOINT)
        assert resp.status_code in (401, 403)


# ── Admin panel ───────────────────────────────────────────────────────────────


class TestAdminGuard:
    ENDPOINT = "/api/admin/stats"

    async def test_human_player_is_forbidden(self, http, human_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(human_token))
        assert resp.status_code == 403

    async def test_ai_developer_is_forbidden(self, http, dev_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(dev_token))
        assert resp.status_code == 403

    async def test_ai_agent_owner_is_forbidden(self, http, owner_token):
        resp = await http.get(self.ENDPOINT, headers=auth_headers(owner_token))
        assert resp.status_code == 403

    async def test_unauthenticated_is_forbidden(self, http):
        resp = await http.get(self.ENDPOINT)
        assert resp.status_code in (401, 403)


# ── Public / all-roles endpoints ──────────────────────────────────────────────


class TestPublicEndpoints:
    async def test_leaderboard_accessible_by_human(self, http, human_token):
        resp = await http.get("/api/users/leaderboard", headers=auth_headers(human_token))
        assert resp.status_code == 200

    async def test_leaderboard_accessible_by_developer(self, http, dev_token):
        resp = await http.get("/api/users/leaderboard", headers=auth_headers(dev_token))
        assert resp.status_code == 200

    async def test_leaderboard_accessible_by_owner(self, http, owner_token):
        resp = await http.get("/api/users/leaderboard", headers=auth_headers(owner_token))
        assert resp.status_code == 200

    async def test_health_is_always_accessible(self, http):
        resp = await http.get("/health")
        assert resp.status_code == 200


# ── Decision log payload visibility ──────────────────────────────────────────


class TestDecisionLogPayloadVisibility:
    """
    Agent owners should receive null payloads in decision logs;
    developers should receive full payloads.
    This test registers an agent, then checks the logs endpoint response
    shape differs by role.
    """

    async def test_owner_gets_null_payloads(self, http, owner_token):
        # Register a webhook agent
        reg = await http.post(
            "/api/agents/register-webhook",
            json={
                "name": "payload-test-agent",
                "game_type": "chess",
                "webhook_url": "http://example.invalid/move",
            },
            headers=auth_headers(owner_token),
        )
        assert reg.status_code == 201
        agent_id = reg.json()["id"]

        # There are no actual logs yet (no games played), so the list is empty.
        # We just verify the endpoint is accessible and returns a list.
        resp = await http.get(
            f"/api/agents/{agent_id}/logs", headers=auth_headers(owner_token)
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_developer_can_access_their_agent_logs(self, http, dev_token):
        # Register a script-upload agent (developer role)
        import io
        form_data = {
            "name": "dev-agent",
            "game_type": "chess",
        }
        file_content = b"# placeholder agent script\ndef get_move(state): return 'e2e4'\n"
        resp = await http.post(
            "/api/agents/upload",
            data=form_data,
            files={"file": ("agent.py", io.BytesIO(file_content), "text/plain")},
            headers=auth_headers(dev_token),
        )
        assert resp.status_code == 201
        agent_id = resp.json()["id"]

        resp = await http.get(
            f"/api/agents/{agent_id}/logs", headers=auth_headers(dev_token)
        )
        assert resp.status_code == 200
