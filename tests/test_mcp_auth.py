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
        # anyio's CancelScope.__exit__ (inside StreamableHTTPSessionManager.run()'s
        # task group) enforces that a cancel scope must be exited from the exact
        # asyncio Task that entered it. pytest-asyncio resumes this module-scoped
        # async-generator fixture's teardown in a different top-level task than the
        # one that entered it, which trips that invariant every time — this is a
        # structural pytest-asyncio/anyio interaction, not fixable via loop_scope
        # tuning (confirmed). Currently harmless: the MCP session manager's task
        # group has no live children at this point since none of this module's
        # tests open a real streaming MCP session — if this file is ever extended
        # to exercise a real session, revisit whether tasks are actually leaking.
        try:
            await stack.__aexit__(None, None, None)
        except RuntimeError as e:
            if "different task" not in str(e):
                raise


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
