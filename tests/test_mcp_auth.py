import pytest
from contextlib import AsyncExitStack
from httpx import AsyncClient, ASGITransport

from agentq.api.app import app, mcp_app


@pytest.fixture(scope="module", autouse=True)
async def _mcp_session_manager():
    """Initialize mcp_app's lifespan once per module to satisfy FastMCP's single-run requirement.

    This is scoped to this module only, not the entire test suite, since only these tests
    interact with /mcp. The exit is suppressed due to pytest-asyncio's task context handling.
    """
    stack = AsyncExitStack()
    await stack.__aenter__()
    await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))

    try:
        yield
    finally:
        # Suppress exit errors from pytest-asyncio running exit in a different task context.
        # The stack will be cleaned up when the process exits.
        try:
            await stack.__aexit__(None, None, None)
        except RuntimeError:
            pass


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
