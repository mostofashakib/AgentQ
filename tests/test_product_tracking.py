from datetime import timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from agentq.api.app import app
from agentq.config import Settings
from agentq.db import engine as db_engine
from agentq.db.models import ProductEvent
from agentq.product_tracking import ProductEventInput, ProductEventTracker
from agentq.utils.time import utc_now


async def test_tracker_hashes_identity_and_sanitizes_metadata():
    async with db_engine.async_session() as session:
        tracker = ProductEventTracker(session, identity_salt="test-salt")
        event = await tracker.track(ProductEventInput(
            feature="trace-search",
            action="completed",
            user_id="person@example.com",
            session_id="session-1",
            metadata={"password": "secret", "query": "person@example.com"},
        ))

        assert event is not None
        assert event.user_id_hash != "person@example.com"
        assert len(event.user_id_hash) == 64
        assert event.metadata_json == {"password": "[REDACTED]", "query": "[REDACTED]"}


async def test_tracker_does_not_store_identity_without_a_salt():
    async with db_engine.async_session() as session:
        event = await ProductEventTracker(session, identity_salt="").track(ProductEventInput(
            feature="run-health", action="viewed", user_id="user-123",
        ))

        assert event is not None
        assert event.user_id_hash is None


async def test_tracking_endpoint_supports_opt_out():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/product-analytics/events",
            headers={"X-AgentQ-Tracking-Opt-Out": "true"},
            json={"feature": "run-health", "action": "viewed"},
        )

    assert response.status_code == 202
    assert response.json() == {"tracked": False, "reason": "opted_out"}
    async with db_engine.async_session() as session:
        assert (await session.execute(select(ProductEvent))).scalars().all() == []


async def test_tracking_write_requires_ingest_access_when_auth_is_enabled(monkeypatch):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "ingest_api_key", "ingest-secret")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.post(
            "/api/product-analytics/events",
            json={"feature": "run-health", "action": "viewed"},
        )
        accepted = await client.post(
            "/api/product-analytics/events",
            headers={"X-AgentQ-API-Key": "ingest-secret"},
            json={"feature": "run-health", "action": "viewed"},
        )

    assert missing.status_code == 401
    assert accepted.status_code == 201


async def test_feature_summary_reports_adoption_and_outcomes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for action, user_id in (
            ("started", "user-a"), ("completed", "user-a"),
            ("started", "user-b"), ("abandoned", "user-b"),
            ("feedback_negative", "user-b"),
        ):
            response = await client.post("/api/product-analytics/events", json={
                "feature": "trace-search", "action": action, "user_id": user_id,
            })
            assert response.status_code == 201

        summary = (await client.get("/api/product-analytics/features")).json()

    feature = summary[0]
    assert feature["feature"] == "trace-search"
    assert feature["event_count"] == 5
    assert feature["started_count"] == 2
    assert feature["completed_count"] == 1
    assert feature["abandoned_count"] == 1
    assert feature["negative_feedback_count"] == 1
    assert feature["completion_rate"] == 0.5


async def test_feature_summary_counts_repeat_users(monkeypatch):
    from agentq.api.routes import product_analytics

    monkeypatch.setattr(product_analytics.settings, "product_analytics_identity_salt", "test-salt")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(2):
            response = await client.post("/api/product-analytics/events", json={
                "feature": "trace-search", "action": "completed", "user_id": "user-a",
            })
            assert response.status_code == 201

        feature = (await client.get("/api/product-analytics/features")).json()[0]

    assert feature["unique_user_count"] == 1
    assert feature["repeat_user_count"] == 1


async def test_product_event_retention_is_independent_from_trace_retention(monkeypatch):
    from agentq.monitoring.retention import prune_expired_telemetry
    from agentq.monitoring import retention

    monkeypatch.setattr(retention.settings, "product_analytics_retention_days", 7)
    async with db_engine.async_session() as session:
        session.add(ProductEvent(feature="old", action="viewed", created_at=utc_now() - timedelta(days=8)))
        session.add(ProductEvent(feature="new", action="viewed", created_at=utc_now()))
        await session.commit()
        await prune_expired_telemetry(session)
        features = list((await session.execute(select(ProductEvent.feature))).scalars())

    assert features == ["new"]


def test_production_product_tracking_defaults_are_private():
    config = Settings(environment="production")

    assert config.product_analytics_enabled is True
    assert config.product_analytics_identity_salt == ""
    assert config.product_analytics_retention_days == 90
