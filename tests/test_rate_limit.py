from httpx import AsyncClient, ASGITransport

from agentq.api.app import app


async def test_requests_within_limit_all_succeed(monkeypatch):
    from agentq.config import settings as env_settings
    from agentq.api import rate_limit

    rate_limit.reset()
    monkeypatch.setattr(env_settings, "rate_limit_per_minute", 5)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(5):
            r = await client.get("/api/traces")
            assert r.status_code == 200


async def test_exceeding_limit_returns_429_with_retry_after(monkeypatch):
    from agentq.config import settings as env_settings
    from agentq.api import rate_limit

    rate_limit.reset()
    monkeypatch.setattr(env_settings, "rate_limit_per_minute", 3)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(3):
            r = await client.get("/api/traces")
            assert r.status_code == 200
        r = await client.get("/api/traces")

    assert r.status_code == 429
    assert "Retry-After" in r.headers


async def test_health_endpoint_is_exempt_from_rate_limit(monkeypatch):
    from agentq.config import settings as env_settings
    from agentq.api import rate_limit

    rate_limit.reset()
    monkeypatch.setattr(env_settings, "rate_limit_per_minute", 1)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(5):
            r = await client.get("/health")
            assert r.status_code == 200


async def test_different_principals_get_independent_limits(monkeypatch):
    from agentq.config import settings as env_settings
    from agentq.api import security, rate_limit

    rate_limit.reset()
    monkeypatch.setattr(env_settings, "rate_limit_per_minute", 1)
    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "viewer_api_key", "viewer-secret")
    monkeypatch.setattr(security.settings, "admin_api_key", "admin-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.get("/api/traces", headers={"X-AgentQ-API-Key": "viewer-secret"})
        assert r1.status_code == 200
        # Same key again — second request in the same window must be limited
        r1_again = await client.get("/api/traces", headers={"X-AgentQ-API-Key": "viewer-secret"})
        assert r1_again.status_code == 429

        # A different principal (admin key) has its own independent counter
        r2 = await client.get("/api/traces", headers={"X-AgentQ-API-Key": "admin-secret"})
        assert r2.status_code == 200
