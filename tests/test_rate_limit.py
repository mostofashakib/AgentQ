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


def test_malformed_utf8_api_key_header_does_not_crash():
    """Test that invalid UTF-8 bytes in X-AgentQ-API-Key header don't cause
    an unhandled UnicodeDecodeError. The malformed bytes should be replaced,
    fail to match any real key, and fall back to IP-based keying (normal flow)."""
    from agentq.api.rate_limit import _key_for
    from agentq.config import settings as env_settings

    # Create a raw ASGI scope with invalid UTF-8 bytes in the header
    scope = {
        "headers": [
            (b"x-agentq-api-key", b"\xff\xfe"),  # Invalid UTF-8 sequence
            (b"content-type", b"application/json"),
        ],
        "client": ("127.0.0.1", 8000),
    }

    # Should not raise UnicodeDecodeError; should fall back to client IP
    key = _key_for(scope)
    assert key == "127.0.0.1"


def test_expired_entries_are_swept_from_counts():
    """Test that expired rate-limit entries are lazily removed from _counts
    to prevent unbounded memory growth. This test directly manipulates timestamps
    to simulate expired windows without waiting 60+ seconds."""
    from agentq.api import rate_limit
    import time

    rate_limit.reset()

    # Manually populate _counts with entries that have expired timestamps
    now = time.monotonic()
    old_timestamp = now - rate_limit._WINDOW_SECONDS - 1  # Expired by 1 second
    recent_timestamp = now - 10  # Still within window

    rate_limit._counts["expired_key_1"] = (5, old_timestamp)
    rate_limit._counts["expired_key_2"] = (3, old_timestamp)
    rate_limit._counts["recent_key"] = (2, recent_timestamp)

    # Before sweep, all three should be present
    assert len(rate_limit._counts) == 3

    # Call the sweep function (simulating what happens every 1000 requests)
    rate_limit._sweep_expired(now)

    # After sweep, only the recent entry should remain
    assert len(rate_limit._counts) == 1
    assert "recent_key" in rate_limit._counts
    assert "expired_key_1" not in rate_limit._counts
    assert "expired_key_2" not in rate_limit._counts
