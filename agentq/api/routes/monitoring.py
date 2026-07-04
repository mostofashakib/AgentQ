from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, delete, desc, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.engine import get_session
from agentq.db.models import AgentRun, ApprovalRequest, EvaluationResult, MonitoringEvent, Span, Violation
from agentq.api.security import require_admin, require_viewer

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"], dependencies=[Depends(require_viewer)])


def _run_dict(run: AgentRun) -> dict:
    return {column.name: getattr(run, column.name) for column in AgentRun.__table__.columns}


@router.get("/runs")
async def list_runs(
    limit: int = Query(100, le=500), model: str | None = None, tool: str | None = None,
    session_id: str | None = None, environment: str | None = None, agent_type: str | None = None,
    status: str | None = None, session: AsyncSession = Depends(get_session),
):
    stmt = select(AgentRun).order_by(desc(AgentRun.created_at)).limit(limit)
    filters = [(AgentRun.session_id, session_id), (AgentRun.environment, environment),
               (AgentRun.agent_type, agent_type), (AgentRun.status, status)]
    for column, value in filters:
        if value:
            stmt = stmt.where(column == value)
    if model:
        stmt = stmt.where(exists(select(Span.id).where(
            Span.trace_id == AgentRun.trace_id, Span.gen_ai_system == model
        )))
    if tool:
        stmt = stmt.where(exists(select(Span.id).where(
            Span.trace_id == AgentRun.trace_id, Span.gen_ai_tool_name == tool
        )))
    return [_run_dict(run) for run in (await session.execute(stmt)).scalars().all()]


@router.get("/runs/{trace_id}")
async def get_run(trace_id: str, session: AsyncSession = Depends(get_session)):
    run = (await session.execute(select(AgentRun).where(AgentRun.trace_id == trace_id))).scalars().first()
    if not run:
        return None
    evaluations = (await session.execute(select(EvaluationResult).where(EvaluationResult.trace_id == trace_id))).scalars().all()
    events = (await session.execute(select(MonitoringEvent).where(MonitoringEvent.trace_id == trace_id))).scalars().all()
    return {**_run_dict(run), "evaluations": [
        {"evaluator": e.evaluator, "status": e.status, "score": e.score, "reason": e.reason} for e in evaluations
    ], "events": [
        {"event_type": e.event_type, "category": e.category, "severity": e.severity, "reason": e.reason,
         "span_id": e.span_id, "metadata": e.metadata_json, "created_at": e.created_at.isoformat()} for e in events
    ]}


@router.delete("/runs/{trace_id}")
async def delete_run_data(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_admin),
):
    """Delete all monitoring data for one trace for privacy/retention workflows."""
    for model in (EvaluationResult, MonitoringEvent, ApprovalRequest, Violation, Span, AgentRun):
        await session.execute(delete(model).where(model.trace_id == trace_id))
    await session.commit()
    return {"deleted_trace_id": trace_id}


@router.get("/metrics")
async def aggregate_metrics(session: AsyncSession = Depends(get_session)):
    row = (await session.execute(select(
        func.count(AgentRun.id),
        func.sum(case((AgentRun.status == "success", 1), else_=0)),
        func.sum(case((AgentRun.status == "failed", 1), else_=0)),
        func.avg(AgentRun.total_latency_ms), func.sum(AgentRun.input_tokens + AgentRun.output_tokens),
        func.sum(AgentRun.estimated_cost_usd), func.sum(AgentRun.tool_call_count),
        func.sum(AgentRun.tool_success_count), func.sum(AgentRun.error_count),
    ))).one()
    latencies = list((await session.execute(select(AgentRun.total_latency_ms).order_by(AgentRun.total_latency_ms))).scalars())
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * .95))] if latencies else 0
    evaluation_rows = (await session.execute(select(EvaluationResult.status, func.count()).group_by(EvaluationResult.status))).all()
    event_rows = (await session.execute(select(MonitoringEvent.event_type, func.count()).group_by(MonitoringEvent.event_type))).all()
    total, successes, failures, avg_latency, tokens, cost, tool_calls, tool_successes, errors = row
    return {"run_volume": total or 0, "success_rate": (successes or 0) / total if total else 0,
            "error_rate": (failures or 0) / total if total else 0, "average_latency_ms": avg_latency or 0,
            "p95_latency_ms": p95, "total_tokens": tokens or 0, "estimated_cost_usd": cost or 0,
            "tool_success_rate": (tool_successes or 0) / tool_calls if tool_calls else 0,
            "error_count": errors or 0, "evaluation_counts": dict(evaluation_rows), "event_counts": dict(event_rows)}


@router.get("/events")
async def list_events(event_type: str | None = None, severity: str | None = None,
                      session: AsyncSession = Depends(get_session)):
    stmt = select(MonitoringEvent).order_by(desc(MonitoringEvent.created_at)).limit(500)
    if event_type:
        stmt = stmt.where(MonitoringEvent.event_type == event_type)
    if severity:
        stmt = stmt.where(MonitoringEvent.severity == severity)
    return [{"id": e.id, "trace_id": e.trace_id, "agent_run_id": e.agent_run_id, "span_id": e.span_id,
             "event_type": e.event_type, "category": e.category, "severity": e.severity,
             "reason": e.reason, "metadata": e.metadata_json, "created_at": e.created_at.isoformat()}
            for e in (await session.execute(stmt)).scalars().all()]
