from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

import agentq.db.engine as db_engine
from agentq.api.app import app
from agentq.db.models import AgentRun, EvaluationResult, Span
from agentq.utils.time import utc_now


@pytest.fixture
async def client(connected_agent_factory):
    token = await connected_agent_factory("agent-a")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-AgentQ-Agent-Token": token}) as value:
        yield value


async def _seed_visible_spans(*trace_ids: str):
    """visible_trace_ids() requires a Span row whose service_name matches a
    registered, enabled, trace-capturing ConnectedAgent -- seed one per trace_id
    so bare AgentRun/EvaluationResult rows aren't invisible to the endpoints."""
    async with db_engine.async_session() as session:
        session.add_all([
            Span(trace_id=trace_id, span_id=f"span-{trace_id}", name="op", span_kind="CLIENT",
                 service_name="agent-a", start_time_unix_nano=1, end_time_unix_nano=2, duration_ms=1.0)
            for trace_id in trace_ids
        ])
        await session.commit()


async def _seed_runs():
    await _seed_visible_spans("t1", "t2", "t3", "t4")
    async with db_engine.async_session() as session:
        session.add_all([
            AgentRun(trace_id="t1", agent_run_id="r1", session_id="sess-a",
                     input_tokens=100, output_tokens=50, estimated_cost_usd=0.5, error_count=1, tool_call_count=2),
            AgentRun(trace_id="t2", agent_run_id="r2", session_id="sess-a",
                     input_tokens=200, output_tokens=100, estimated_cost_usd=1.5, tool_call_count=1),
            AgentRun(trace_id="t3", agent_run_id="r3", session_id="sess-b",
                     input_tokens=10, output_tokens=5, estimated_cost_usd=0.01),
            AgentRun(trace_id="t4", agent_run_id="r4", session_id=None, estimated_cost_usd=9.0),
        ])
        await session.commit()


async def test_sessions_endpoint_aggregates_cost(client):
    await _seed_runs()
    rows = (await client.get("/api/monitoring/sessions")).json()
    assert [row["session_id"] for row in rows] == ["sess-a", "sess-b"]  # cost desc, null excluded
    top = rows[0]
    assert top["run_count"] == 2 and top["total_tokens"] == 450
    assert top["estimated_cost_usd"] == 2.0 and top["error_count"] == 1 and top["tool_call_count"] == 3


async def test_quality_trends_buckets_by_day(client):
    await _seed_visible_spans("t1", "t2", "t3", "old")
    now = utc_now()
    async with db_engine.async_session() as session:
        session.add_all([
            EvaluationResult(trace_id="t1", agent_run_id="r1", evaluator="faithfulness", status="pass",
                             created_at=now - timedelta(days=1)),
            EvaluationResult(trace_id="t2", agent_run_id="r2", evaluator="faithfulness", status="fail",
                             created_at=now),
            EvaluationResult(trace_id="t3", agent_run_id="r3", evaluator="relevancy", status="warn",
                             created_at=now),
            EvaluationResult(trace_id="old", agent_run_id="r0", evaluator="faithfulness", status="fail",
                             created_at=now - timedelta(days=30)),   # outside window
        ])
        await session.commit()
    body = (await client.get("/api/monitoring/quality-trends?days=7")).json()
    assert body["totals"]["faithfulness"] == {"pass": 1, "warn": 0, "fail": 1}
    assert body["totals"]["relevancy"] == {"pass": 0, "warn": 1, "fail": 0}
    assert len(body["days"]) == 2
    assert body["days"] == sorted(body["days"], key=lambda d: d["date"])
    today = body["days"][-1]["evaluators"]
    assert today["faithfulness"]["fail"] == 1
