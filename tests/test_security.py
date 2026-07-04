from httpx import ASGITransport, AsyncClient
import asyncio

from agentq.api.app import app
from agentq.config import Settings


async def test_protected_write_rejects_missing_api_key(monkeypatch):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "admin_api_key", "admin-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/api/monitoring/runs/trace-1")

    assert response.status_code == 401


async def test_viewer_key_cannot_decide_approval(monkeypatch):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "viewer_api_key", "viewer-secret")
    monkeypatch.setattr(security.settings, "admin_api_key", "admin-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/approvals/not-found/decision",
            headers={"X-AgentQ-API-Key": "viewer-secret"},
            json={"decision": "approved", "reviewer_id": "claimed-admin"},
        )

    assert response.status_code == 403


async def test_admin_key_can_reach_protected_endpoint(monkeypatch):
    from agentq.api import security

    monkeypatch.setattr(security.settings, "api_auth_enabled", True)
    monkeypatch.setattr(security.settings, "admin_api_key", "admin-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/api/monitoring/runs/trace-1",
            headers={"X-AgentQ-API-Key": "admin-secret"},
        )

    assert response.status_code == 200


def test_production_configuration_enables_authentication_by_default():
    config = Settings(environment="production")

    assert config.auth_required is True
    assert "*" not in config.allowed_cors_origins


def test_collection_defaults_are_not_shared():
    from agentq.api.routes.alerts import AlertRuleBody
    from agentq.api.routes.intercept import InterceptRequest, InterceptResponse
    from agentq.db.models import SpanRecord

    first_rule, second_rule = AlertRuleBody(name="one"), AlertRuleBody(name="two")
    first_rule.channels.append({"type": "webhook"})
    assert second_rule.channels == []

    first_request = InterceptRequest(trace_id="t1", span_id="s1", tool_name="tool")
    second_request = InterceptRequest(trace_id="t2", span_id="s2", tool_name="tool")
    first_request.attributes["changed"] = True
    assert second_request.attributes == {}

    first_response, second_response = InterceptResponse(allowed=True), InterceptResponse(allowed=True)
    first_response.violations.append({"rule_id": "one"})
    assert second_response.violations == []

    first_span = SpanRecord(
        trace_id="t1", span_id="s1", name="one", span_kind="CLIENT", service_name="test",
        start_time_unix_nano=1, end_time_unix_nano=2, duration_ms=0.000001,
    )
    second_span = SpanRecord(
        trace_id="t2", span_id="s2", name="two", span_kind="CLIENT", service_name="test",
        start_time_unix_nano=1, end_time_unix_nano=2, duration_ms=0.000001,
    )
    first_span.attributes["changed"] = True
    assert second_span.attributes == {}


def test_utc_now_is_timezone_aware():
    from agentq.utils.time import utc_now

    timestamp = utc_now()

    assert timestamp.utcoffset() is not None
    assert timestamp.utcoffset().total_seconds() == 0


async def test_background_task_group_cancels_and_awaits_workers():
    from agentq.utils.tasks import BackgroundTaskGroup

    stopped = asyncio.Event()

    async def worker() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    async with BackgroundTaskGroup() as tasks:
        tasks.start(worker(), name="test-worker")
        await asyncio.sleep(0)

    assert stopped.is_set()
