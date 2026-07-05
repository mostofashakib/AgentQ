import json
import logging
import pytest
from httpx import ASGITransport, AsyncClient

import agentq.db.engine as db_engine
from agentq.api.app import app

from agentq.config import Settings
from agentq.db.models import AgentRun, MonitoringEvent, SpanRecord
from agentq.monitoring.emitter import AGGREGATE_TRACE_ID
from agentq.monitoring.anomaly import detect_run_anomalies
from agentq.monitoring.cost import estimate_cost
from agentq.monitoring.evaluators import evaluate_span
from agentq.monitoring.logging import log_event
from agentq.monitoring.redaction import REDACTED, redact, sanitize_span_attributes
from agentq.monitoring.runs import circuit_breaker_reason


@pytest.fixture
async def client(connected_agent_factory):
    token = await connected_agent_factory("agent-a")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-AgentQ-Agent-Token": token}) as value:
        yield value


def make_span(**overrides):
    values = dict(trace_id="trace-monitor", span_id="span-monitor", name="chat", span_kind="CLIENT",
                  service_name="test-agent", start_time_unix_nano=1, end_time_unix_nano=2_000_001,
                  duration_ms=2.0, gen_ai_system="openai", gen_ai_operation="chat")
    values.update(overrides)
    return SpanRecord(**values)


def test_redaction_recurses_and_masks_common_secrets():
    result = redact({"password": "hunter2", "nested": {"token": "secret", "message": "email a@b.com sk-secret12345"}})
    assert result["password"] == REDACTED
    assert result["nested"]["token"] == REDACTED
    assert "a@b.com" not in result["nested"]["message"]
    assert "sk-secret12345" not in result["nested"]["message"]


def test_raw_content_omitted_by_default_even_before_redaction():
    result = sanitize_span_attributes({"gen_ai.prompt": "private", "gen_ai.completion": "private"}, False, False)
    assert result == {"gen_ai.prompt": "[OMITTED]", "gen_ai.completion": "[OMITTED]"}


def test_production_defaults_disable_raw_content():
    config = Settings(environment="production")
    assert not config.raw_prompt_logging_enabled
    assert not config.raw_output_logging_enabled


def test_cost_estimation_supports_known_and_unknown_models():
    assert estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000) == 0.75
    assert estimate_cost("unknown-provider-model", 1_000_000, 1_000_000) == 18.0


def test_structured_log_redacts(caplog):
    with caplog.at_level(logging.INFO, logger="agentq.monitoring"):
        log_event("tool_call", trace_id="t1", agent_run_id="r1", session_id="s1", api_key="sk-secret12345")
    payload = json.loads(caplog.records[-1].message)
    assert payload["trace_id"] == "t1"
    assert payload["api_key"] == REDACTED


def test_evaluators_have_clear_statuses_and_reasons():
    results = evaluate_span(make_span(attributes={}), {"behavioral.hallucinated_tool"})
    assert {result.evaluator for result in results} == {
        "faithfulness", "relevancy", "completeness", "hallucination_risk", "policy_adherence"
    }
    assert all(result.status in {"pass", "warn", "fail"} for result in results)
    assert next(r for r in results if r.evaluator == "hallucination_risk").status == "fail"


def test_circuit_breaker_stops_at_limit(monkeypatch):
    from agentq.monitoring import runs
    monkeypatch.setattr(runs.settings, "max_tool_calls", 2)
    run = AgentRun(trace_id="t", agent_run_id="r", tool_call_count=2)
    assert circuit_breaker_reason(run) == ("blocked", "maximum tool calls reached")


def test_anomaly_thresholds(monkeypatch):
    from agentq.monitoring import anomaly
    monkeypatch.setattr(anomaly.settings, "unusual_latency_ms", 10)
    run = AgentRun(trace_id="t", agent_run_id="r", total_latency_ms=20)
    assert any(item.category == "latency_spike" for item in detect_run_anomalies(run))


async def test_full_run_metrics_and_approval_flow(client):
    payload = {
        "resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "agent-a"}}]},
          "scopeSpans": [{"spans": [{"traceId": "full-run", "spanId": "root", "name": "agent run", "kind": 2,
            "startTimeUnixNano": "1000000", "endTimeUnixNano": "5000000", "attributes": [
              {"key": "agentq.session_id", "value": {"stringValue": "session-a"}},
              {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
              {"key": "gen_ai.usage.input_tokens", "value": {"intValue": 100}},
              {"key": "gen_ai.usage.output_tokens", "value": {"intValue": 50}},
            ], "status": {"code": "STATUS_CODE_OK"}}]}]}]
    }
    assert (await client.post("/v1/traces", json=payload)).status_code == 200
    run = (await client.get("/api/monitoring/runs/full-run")).json()
    assert run["session_id"] == "session-a"
    assert run["input_tokens"] == 100
    assert run["status"] == "success"

    held = (await client.post("/api/intercept", json={
        "trace_id": "full-run", "span_id": "email-1", "tool_name": "send_email",
        "service_name": "agent-a",
        "attributes": {"recipient": "private@example.com"},
    })).json()
    assert held["allowed"] is False
    assert held["status"] == "requires_human_review"
    approved = (await client.post(f"/api/approvals/{held['approval_request_id']}/decision", json={
        "decision": "approved", "reviewer_id": "reviewer-1", "reason": "Validated recipient",
    })).json()
    assert approved["status"] == "approved"
    retry = (await client.post("/api/intercept", json={
        "trace_id": "full-run", "span_id": "email-1", "tool_name": "send_email",
        "service_name": "agent-a",
    })).json()
    assert retry["allowed"] is True

    metrics = (await client.get("/api/monitoring/metrics")).json()
    assert metrics["run_volume"] == 1


async def test_aggregate_events_visible_without_owning_trace(client):
    """Aggregate (trace_id="aggregate") events have no Span/AgentRun/connected-agent
    row, so visible_trace_ids() alone would hide them; the routes must include them."""
    async with db_engine.async_session() as session:
        session.add(MonitoringEvent(
            trace_id=AGGREGATE_TRACE_ID, event_type="anomaly", category="error_rate_spike",
            severity="high", reason="test",
        ))
        await session.commit()

    events = (await client.get("/api/monitoring/events")).json()
    assert any(e["trace_id"] == AGGREGATE_TRACE_ID and e["category"] == "error_rate_spike" for e in events)

    filtered = (await client.get("/api/monitoring/events", params={"event_type": "anomaly"})).json()
    assert any(e["trace_id"] == AGGREGATE_TRACE_ID and e["category"] == "error_rate_spike" for e in filtered)

    metrics = (await client.get("/api/monitoring/metrics")).json()
    assert metrics["event_counts"].get("anomaly", 0) >= 1
