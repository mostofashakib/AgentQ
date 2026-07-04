from httpx import AsyncClient, ASGITransport

from agentq.api.app import app


async def test_mcp_mount_rejects_missing_api_key(monkeypatch):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "admin_api_key", "admin-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
        response = await client.post("/mcp", json={})

    assert response.status_code == 401


async def test_mcp_mount_accepts_any_valid_key_tier(monkeypatch):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "ingest_api_key", "ingest-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
        response = await client.post(
            "/mcp", json={}, headers={"X-AgentQ-API-Key": "ingest-secret"},
        )

    # The auth gate let the request through to FastMCP itself — whatever
    # FastMCP does with a malformed/empty JSON-RPC body is out of scope here,
    # but it must not be the auth middleware's own 401.
    assert response.status_code != 401


async def test_mcp_mount_open_when_auth_not_required(monkeypatch):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
        response = await client.post("/mcp", json={})

    assert response.status_code != 401
