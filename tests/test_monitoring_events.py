import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import agentq.db.engine as db_engine
from agentq.api.app import app
from agentq.db.models import MonitoringEvent
from agentq.events import alert_event_queue, MonitoringAlertEvent
from agentq.monitoring.emitter import emit_monitoring_event


def _drain(queue):
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
        queue.task_done()
    return items


@pytest.fixture(autouse=True)
def _clean_queue():
    _drain(alert_event_queue)
    yield
    _drain(alert_event_queue)


@pytest.fixture
async def client(connected_agent_factory):
    token = await connected_agent_factory("agent-a")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-AgentQ-Agent-Token": token}) as value:
        yield value


async def test_emit_persists_row_and_enqueues_alert():
    async with db_engine.async_session() as session:
        event = await emit_monitoring_event(
            session, trace_id="t1", event_type="circuit_breaker", category="run_limit",
            severity="high", reason="maximum tool calls reached", agent_run_id="r1", span_id="s1",
        )
        await session.commit()
    assert event.id is not None
    async with db_engine.async_session() as session:
        rows = (await session.execute(select(MonitoringEvent))).scalars().all()
    assert len(rows) == 1 and rows[0].category == "run_limit"
    queued = _drain(alert_event_queue)
    assert len(queued) == 1
    assert isinstance(queued[0], MonitoringAlertEvent)
    assert queued[0].event_type == "circuit_breaker"
    assert queued[0].trace_id == "t1" and queued[0].severity == "high"


async def test_emit_with_notify_false_skips_queue():
    async with db_engine.async_session() as session:
        await emit_monitoring_event(
            session, trace_id="t2", event_type="security", category="x",
            severity="critical", reason="already alerted as violation", notify=False,
        )
        await session.commit()
    assert alert_event_queue.empty()


async def test_rejected_approval_enqueues_monitoring_alert(client):
    # NOTE: the `client` fixture above already registers "agent-a" via
    # connected_agent_factory (mirroring tests/test_monitoring.py), using the
    # default TEST_AGENT_TOKEN. Calling connected_agent_factory("agent-a")
    # again here would violate ConnectedAgent.service_name's unique
    # constraint, so we reuse the token the fixture already established.
    from tests.conftest import TEST_AGENT_TOKEN
    payload = {
        "resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "agent-a"}}]},
          "scopeSpans": [{"spans": [{"traceId": "appr-trace", "spanId": "root", "name": "run", "kind": 2,
            "startTimeUnixNano": "1000000", "endTimeUnixNano": "2000000", "attributes": [],
            "status": {"code": "STATUS_CODE_OK"}}]}]}]
    }
    assert (await client.post("/v1/traces", json=payload)).status_code == 200
    resp = await client.post("/api/intercept", json={
        "trace_id": "appr-trace", "span_id": "s-approve", "tool_name": "send_email",
        "service_name": "agent-a", "attributes": {},
    }, headers={"X-AgentQ-Agent-Token": TEST_AGENT_TOKEN})
    body = resp.json()
    assert body["allowed"] is False and body["approval_request_id"]
    _drain(alert_event_queue)
    decision = await client.post(f"/api/approvals/{body['approval_request_id']}/decision",
                                 json={"decision": "rejected", "reviewer_id": "rev-1", "reason": "too risky"})
    assert decision.status_code == 200
    queued = _drain(alert_event_queue)
    approvals = [e for e in queued if isinstance(e, MonitoringAlertEvent) and e.event_type == "approval"]
    assert len(approvals) == 1 and approvals[0].category == "rejected" and approvals[0].severity == "high"
