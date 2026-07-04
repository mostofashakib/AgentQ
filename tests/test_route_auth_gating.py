import pytest
from httpx import AsyncClient, ASGITransport

from agentq.api.app import app


@pytest.mark.parametrize("method,path", [
    ("get", "/api/traces"),
    ("get", "/api/violations"),
    ("get", "/api/graph"),
    ("get", "/api/agents"),
    ("get", "/api/stream"),
    ("get", "/api/behaviors"),
    ("get", "/api/behaviors/test-cluster-id"),
    ("get", "/api/behaviors/test-cluster-id/traces"),
])
async def test_dashboard_read_routes_reject_missing_key_when_auth_required(monkeypatch, method, path):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "viewer_api_key", "viewer-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await getattr(client, method)(path)

    assert response.status_code == 401


@pytest.mark.parametrize("method,path", [
    ("get", "/api/traces"),
    ("get", "/api/violations"),
    ("get", "/api/graph"),
    ("get", "/api/agents"),
    ("get", "/api/behaviors"),
])
async def test_dashboard_read_routes_accept_viewer_key(monkeypatch, method, path):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "viewer_api_key", "viewer-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await getattr(client, method)(path, headers={"X-AgentQ-API-Key": "viewer-secret"})

    assert response.status_code == 200


@pytest.mark.parametrize("method,path", [
    ("get", "/api/behaviors/test-cluster-id"),
    ("get", "/api/behaviors/test-cluster-id/traces"),
])
async def test_behaviors_path_parameterized_routes_accept_viewer_key(monkeypatch, method, path):
    """Path-parameterized routes return 404 for nonexistent IDs, but the key point
    is that auth let the request through (vs. 401). A non-401 response proves auth gating works."""
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "viewer_api_key", "viewer-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await getattr(client, method)(path, headers={"X-AgentQ-API-Key": "viewer-secret"})

    assert response.status_code != 401


async def test_demo_router_rejects_missing_key_when_auth_required(monkeypatch):
    """demo.py's router is only mounted onto the shared `app` singleton when
    settings.demo_mode was True at process start (agentq/api/app.py's
    `if settings.demo_mode: app.include_router(...)` runs once at import
    time) — monkeypatching demo_mode inside a test has no effect on an
    already-built `app`. Build a minimal standalone FastAPI app that always
    includes the router instead, so this test exercises the router's own
    `dependencies=[Depends(require_admin)]` gating directly, independent of
    whatever DEMO_MODE the real app happened to start with."""
    from fastapi import FastAPI
    from agentq.api import security
    from agentq.api.routes import demo as demo_route

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "admin_api_key", "admin-secret")

    test_app = FastAPI()
    test_app.include_router(demo_route.router)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/api/demo/seed")

    assert response.status_code == 401


async def test_demo_router_rejects_viewer_key(monkeypatch):
    from fastapi import FastAPI
    from agentq.api import security
    from agentq.api.routes import demo as demo_route

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "viewer_api_key", "viewer-secret")
    monkeypatch.setattr(security.settings, "admin_api_key", "admin-secret")

    test_app = FastAPI()
    test_app.include_router(demo_route.router)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(
            "/api/demo/seed", headers={"X-AgentQ-API-Key": "viewer-secret"},
        )

    assert response.status_code == 403
