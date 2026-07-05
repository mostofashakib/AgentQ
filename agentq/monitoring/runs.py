from __future__ import annotations

import hashlib
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.config import settings
from agentq.db.models import AgentRun, EvaluationResult, MonitoringEvent, Span
from agentq.monitoring.anomaly import detect_run_anomalies
from agentq.monitoring.cost import estimate_cost
from agentq.monitoring.emitter import emit_monitoring_event
from agentq.monitoring.logging import log_event


def _stable_run_id(trace_id: str) -> str:
    return f"run_{hashlib.sha256(trace_id.encode()).hexdigest()[:24]}"


def _model_name(span: Span) -> str | None:
    return span.attributes.get("gen_ai.request.model") or span.attributes.get("gen_ai.response.model") or span.gen_ai_system


def _is_model_call(span: Span) -> bool:
    return bool(span.gen_ai_system or span.gen_ai_operation in {"chat", "completion", "embeddings"})


def _is_tool_call(span: Span) -> bool:
    return bool(span.gen_ai_tool_name)


async def aggregate_run(session: AsyncSession, trace_id: str) -> AgentRun:
    spans = (await session.execute(
        select(Span).where(Span.trace_id == trace_id).order_by(Span.start_time_unix_nano)
    )).scalars().all()
    if not spans:
        raise ValueError(f"Cannot aggregate empty trace {trace_id}")

    run = (await session.execute(select(AgentRun).where(AgentRun.trace_id == trace_id))).scalars().first()
    if run is None:
        run = AgentRun(trace_id=trace_id, agent_run_id=_stable_run_id(trace_id))
        session.add(run)

    model_spans = [span for span in spans if _is_model_call(span)]
    tool_spans = [span for span in spans if _is_tool_call(span)]
    errors = [span for span in spans if span.status_code == "STATUS_CODE_ERROR"]
    run.session_id = next((str(s.attributes.get("session.id") or s.attributes.get("agentq.session_id"))
                           for s in spans if s.attributes.get("session.id") or s.attributes.get("agentq.session_id")), None)
    run.agent_type = spans[0].service_name
    run.environment = str(spans[0].attributes.get("deployment.environment.name", settings.environment))
    run.started_at_unix_nano = min(s.start_time_unix_nano for s in spans)
    run.ended_at_unix_nano = max(s.end_time_unix_nano for s in spans)
    run.total_latency_ms = max(0.0, (run.ended_at_unix_nano - run.started_at_unix_nano) / 1_000_000)
    run.input_tokens = sum(s.gen_ai_input_tokens or 0 for s in model_spans)
    run.output_tokens = sum(s.gen_ai_output_tokens or 0 for s in model_spans)
    run.estimated_cost_usd = sum(estimate_cost(_model_name(s), s.gen_ai_input_tokens or 0, s.gen_ai_output_tokens or 0) for s in model_spans)
    run.error_count = len(errors)
    run.error_types = sorted({str(s.attributes.get("error.type", "unknown")) for s in errors})
    run.model_call_count = len(model_spans)
    run.tool_call_count = len(tool_spans)
    run.tool_failure_count = sum(s.status_code == "STATUS_CODE_ERROR" for s in tool_spans)
    run.tool_success_count = len(tool_spans) - run.tool_failure_count
    run.retry_count = sum(int(s.attributes.get("agentq.retry_count", 0) or 0) for s in spans)
    run.step_count = len(spans)
    explicit_status = next((s.attributes.get("agentq.run_status") for s in reversed(spans) if s.attributes.get("agentq.run_status")), None)
    run.status = str(explicit_status or ("failed" if errors else "success"))
    await session.flush()

    previous_categories = set((await session.execute(
        select(MonitoringEvent.category).where(
            MonitoringEvent.trace_id == trace_id, MonitoringEvent.event_type == "anomaly")
    )).scalars())
    await session.execute(delete(MonitoringEvent).where(
        MonitoringEvent.trace_id == trace_id, MonitoringEvent.event_type == "anomaly"
    ))
    for anomaly in detect_run_anomalies(run):
        await emit_monitoring_event(
            session, trace_id=trace_id, agent_run_id=run.agent_run_id,
            event_type="anomaly", category=anomaly.category, severity=anomaly.severity,
            reason=anomaly.reason, notify=anomaly.category not in previous_categories,
        )
    log_event("agent_run_updated", trace_id=trace_id, agent_run_id=run.agent_run_id,
              session_id=run.session_id, status=run.status, latency_ms=run.total_latency_ms,
              tokens=run.input_tokens + run.output_tokens, cost_usd=run.estimated_cost_usd)
    return run


def circuit_breaker_reason(run: AgentRun, tool_name: str | None = None, similar_tool_calls: int = 0) -> tuple[str, str] | None:
    checks = [
        ((run.step_count or 0) >= settings.max_agent_steps, "blocked", "maximum agent steps reached"),
        ((run.model_call_count or 0) >= settings.max_model_calls, "blocked", "maximum model calls reached"),
        ((run.tool_call_count or 0) >= settings.max_tool_calls, "blocked", "maximum tool calls reached"),
        ((run.retry_count or 0) >= settings.max_retries, "blocked", "maximum retries reached"),
        ((run.total_latency_ms or 0) >= settings.max_runtime_seconds * 1000, "timed_out", "maximum runtime reached"),
        ((run.input_tokens or 0) + (run.output_tokens or 0) >= settings.max_tokens_per_run, "blocked", "maximum token usage reached"),
        ((run.estimated_cost_usd or 0) >= settings.max_cost_usd_per_run, "blocked", "maximum estimated cost reached"),
        (similar_tool_calls >= settings.max_similar_tool_calls, "blocked", f"repeated similar call to {tool_name}"),
    ]
    return next(((status, reason) for exceeded, status, reason in checks if exceeded), None)


async def record_evaluations(session: AsyncSession, trace_id: str, evaluations) -> None:
    run = (await session.execute(select(AgentRun).where(AgentRun.trace_id == trace_id))).scalars().first()
    if not run:
        return
    for result in evaluations:
        existing = (await session.execute(select(EvaluationResult).where(
            EvaluationResult.trace_id == trace_id, EvaluationResult.evaluator == result.evaluator
        ))).scalars().first()
        previous_status = existing.status if existing else None
        if existing is None:
            existing = EvaluationResult(trace_id=trace_id, agent_run_id=run.agent_run_id, evaluator=result.evaluator,
                                        status=result.status, score=result.score, reason=result.reason)
            session.add(existing)
        else:
            existing.status, existing.score, existing.reason = result.status, result.score, result.reason
        if result.status == "fail" and previous_status != "fail":
            severity = "high" if result.evaluator in {"hallucination_risk", "policy_adherence"} else "medium"
            await emit_monitoring_event(
                session, trace_id=trace_id, agent_run_id=run.agent_run_id,
                event_type="evaluation", category=result.evaluator, severity=severity,
                reason=result.reason or f"{result.evaluator} evaluation failed",
            )
