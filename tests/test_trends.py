from datetime import timedelta

import pytest
from sqlalchemy import select

import agentq.db.engine as db_engine
from agentq.db.models import AgentRun, MonitoringEvent, Span
from agentq.monitoring.anomaly import detect_format_change
from agentq.monitoring.trends import detect_trend_anomalies, run_trend_check
from agentq.utils.time import utc_now


def _run(idx: int, *, minutes_ago: float, status="success", latency=100.0, cost=0.001):
    now = utc_now()
    return AgentRun(trace_id=f"tr-{idx}", agent_run_id=f"run-{idx}", status=status,
                    total_latency_ms=latency, estimated_cost_usd=cost,
                    created_at=now - timedelta(minutes=minutes_ago),
                    updated_at=now - timedelta(minutes=minutes_ago))


async def _seed(runs):
    async with db_engine.async_session() as session:
        session.add_all(runs)
        await session.commit()


async def test_error_rate_spike_detected(monkeypatch):
    from agentq.monitoring import trends
    monkeypatch.setattr(trends.settings, "trend_min_runs", 5)
    baseline = [_run(i, minutes_ago=40) for i in range(10)]                      # 0% errors
    recent = [_run(100 + i, minutes_ago=5, status="failed") for i in range(5)]   # 100% errors
    await _seed(baseline + recent)
    async with db_engine.async_session() as session:
        anomalies = await detect_trend_anomalies(session)
    assert any(a.category == "error_rate_spike" for a in anomalies)


async def test_quiet_when_rates_are_stable():
    await _seed([_run(i, minutes_ago=40) for i in range(10)] + [_run(100 + i, minutes_ago=5) for i in range(6)])
    async with db_engine.async_session() as session:
        anomalies = await detect_trend_anomalies(session)
    assert anomalies == []


async def test_quiet_below_min_runs(monkeypatch):
    from agentq.monitoring import trends
    monkeypatch.setattr(trends.settings, "trend_min_runs", 5)
    await _seed([_run(i, minutes_ago=40) for i in range(10)] + [_run(100, minutes_ago=5, status="failed")])
    async with db_engine.async_session() as session:
        anomalies = await detect_trend_anomalies(session)
    assert not any(a.category == "error_rate_spike" for a in anomalies)


async def test_run_trend_check_emits_once_within_window(monkeypatch):
    from agentq.monitoring import trends
    monkeypatch.setattr(trends.settings, "trend_min_runs", 5)
    baseline = [_run(i, minutes_ago=40) for i in range(10)]
    recent = [_run(100 + i, minutes_ago=5, status="failed") for i in range(5)]
    await _seed(baseline + recent)
    async with db_engine.async_session() as session:
        first = await run_trend_check(session)
    async with db_engine.async_session() as session:
        second = await run_trend_check(session)   # deduped: event already exists in window
    assert first and not second
    async with db_engine.async_session() as session:
        events = (await session.execute(select(MonitoringEvent).where(
            MonitoringEvent.category == "error_rate_spike"))).scalars().all()
    assert len(events) == 1 and events[0].trace_id == "aggregate"


def test_format_change_detected():
    def span(fmt):
        return Span(trace_id="t", span_id=f"s-{fmt}-{id(fmt)}", name="llm", span_kind="CLIENT",
                    service_name="agent", start_time_unix_nano=0, end_time_unix_nano=0,
                    duration_ms=1.0, gen_ai_system="openai",
                    attributes={"agentq.output_format": fmt} if fmt else {})
    assert any(a.category == "output_format_change" for a in detect_format_change([span("json"), span("text")]))
    assert detect_format_change([span("json"), span("json")]) == []
    assert detect_format_change([span(None), span(None)]) == []
