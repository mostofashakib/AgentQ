"""Aggregate (cross-run) trend anomaly detection: recent window vs baseline window."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import agentq.db.engine as _db_engine
from agentq.config import settings
from agentq.db.models import AgentRun, MonitoringEvent
from agentq.monitoring.anomaly import Anomaly
from agentq.monitoring.emitter import AGGREGATE_TRACE_ID, emit_monitoring_event
from agentq.utils.time import ensure_utc, utc_now

logger = logging.getLogger(__name__)


async def detect_trend_anomalies(session: AsyncSession) -> list[Anomaly]:
    now = utc_now()
    recent_cutoff = now - timedelta(minutes=settings.trend_window_minutes)
    baseline_cutoff = recent_cutoff - timedelta(minutes=settings.trend_baseline_minutes)
    runs = (await session.execute(select(AgentRun).where(AgentRun.updated_at >= baseline_cutoff))).scalars().all()
    recent = [run for run in runs if ensure_utc(run.updated_at) >= recent_cutoff]
    baseline = [run for run in runs if ensure_utc(run.updated_at) < recent_cutoff]
    if len(recent) < settings.trend_min_runs or len(baseline) < settings.trend_min_runs:
        return []

    multiplier = settings.trend_spike_multiplier
    results: list[Anomaly] = []

    def _rate(group: list[AgentRun]) -> float:
        return sum(run.status == "failed" for run in group) / len(group)

    def _avg(group: list[AgentRun], attribute: str) -> float:
        return sum(getattr(run, attribute) or 0 for run in group) / len(group)

    recent_errors, baseline_errors = _rate(recent), _rate(baseline)
    if recent_errors >= max(baseline_errors * multiplier, 0.2) and recent_errors > baseline_errors:
        results.append(Anomaly("error_rate_spike", "high",
                               f"Error rate rose to {recent_errors:.0%} over the last {settings.trend_window_minutes}m "
                               f"(baseline {baseline_errors:.0%})"))

    recent_latency, baseline_latency = _avg(recent, "total_latency_ms"), _avg(baseline, "total_latency_ms")
    if baseline_latency > 0 and recent_latency >= baseline_latency * multiplier:
        results.append(Anomaly("aggregate_latency_spike", "high",
                               f"Average run latency rose to {recent_latency:.0f}ms "
                               f"(baseline {baseline_latency:.0f}ms)"))

    recent_cost, baseline_cost = _avg(recent, "estimated_cost_usd"), _avg(baseline, "estimated_cost_usd")
    if baseline_cost > 0 and recent_cost >= baseline_cost * multiplier:
        results.append(Anomaly("aggregate_cost_spike", "high",
                               f"Average run cost rose to ${recent_cost:.4f} (baseline ${baseline_cost:.4f})"))
    return results


async def run_trend_check(session: AsyncSession) -> list[Anomaly]:
    """Detect, dedupe against events already emitted inside the window, emit, commit."""
    anomalies = await detect_trend_anomalies(session)
    if not anomalies:
        return []
    window_start = utc_now() - timedelta(minutes=settings.trend_window_minutes)
    already = set((await session.execute(select(MonitoringEvent.category).where(
        MonitoringEvent.trace_id == AGGREGATE_TRACE_ID,
        MonitoringEvent.event_type == "anomaly",
        MonitoringEvent.created_at >= window_start,
    ))).scalars())
    emitted = [anomaly for anomaly in anomalies if anomaly.category not in already]
    for anomaly in emitted:
        await emit_monitoring_event(session, trace_id=AGGREGATE_TRACE_ID, event_type="anomaly",
                                    category=anomaly.category, severity=anomaly.severity, reason=anomaly.reason)
    await session.commit()
    return emitted


async def trend_worker() -> None:
    while True:
        await asyncio.sleep(settings.trend_check_interval_seconds)
        try:
            async with _db_engine.async_session() as session:
                await run_trend_check(session)
        except Exception:
            logger.exception("trend_worker check failed")
