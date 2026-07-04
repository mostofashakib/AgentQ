"""
Pre-execution tool intercept endpoint.

Agents call POST /api/intercept BEFORE executing a tool. AgentQ runs the
guardrail engine against a synthetic SpanRecord and returns an allow/deny
decision immediately so the agent can halt before side effects occur.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Any
from agentq.guardrails.intercept import check_action
from agentq.config import settings
from agentq.db.engine import get_session
from agentq.db.models import AgentRun, ApprovalRequest, MonitoringEvent, Span
from agentq.monitoring.redaction import redact
from agentq.monitoring.runs import circuit_breaker_reason

router = APIRouter(prefix="/api")


class InterceptRequest(BaseModel):
    trace_id: str
    span_id: str
    tool_name: str
    service_name: str = "unknown"
    attributes: dict[str, Any] = {}


class InterceptResponse(BaseModel):
    allowed: bool
    rule_id: str | None = None
    reason: str | None = None
    violations: list[dict] = []
    approval_request_id: str | None = None
    status: str | None = None


@router.post("/intercept", response_model=InterceptResponse)
async def intercept_tool_call(req: InterceptRequest, session: AsyncSession = Depends(get_session)) -> InterceptResponse:
    """
    Run guardrail checks before a tool executes. Returns immediately.

    Usage (Python):
        resp = httpx.post("http://localhost:8000/api/intercept", json={
            "trace_id": current_trace_id,
            "span_id": new_span_id,
            "tool_name": "send_email",
            "attributes": {"agentq.user_confirmed": False}
        })
        # always allowed=true; inspect violations before executing
        violations = resp.json()["violations"]
    """
    violations = await check_action(
        trace_id=req.trace_id,
        span_id=req.span_id,
        tool_name=req.tool_name,
        service_name=req.service_name,
        attributes=req.attributes,
    )
    run = (await session.execute(select(AgentRun).where(AgentRun.trace_id == req.trace_id))).scalars().first()
    repeated = (await session.execute(select(func.count()).select_from(Span).where(
        Span.trace_id == req.trace_id, Span.gen_ai_tool_name == req.tool_name
    ))).scalar_one()
    breaker = circuit_breaker_reason(run, req.tool_name, repeated) if run else None
    blocking_violation = next((v for v in violations if v.severity in {"high", "critical"}), None)

    if breaker:
        status, reason = breaker
        run.status, run.terminal_reason = status, reason
        session.add(MonitoringEvent(trace_id=req.trace_id, agent_run_id=run.agent_run_id,
                                    span_id=req.span_id, event_type="circuit_breaker", category="run_limit",
                                    severity="high", reason=reason))
        await session.commit()
        return InterceptResponse(allowed=False, rule_id="circuit_breaker", reason=reason,
                                 violations=[v.model_dump() for v in violations], status=status)

    if blocking_violation and blocking_violation.rule_id in {
        "scope.unsanctioned_tool", "injection.system_prompt_override", "exfiltration.sensitive_key_in_output"
    }:
        session.add(MonitoringEvent(trace_id=req.trace_id, agent_run_id=run.agent_run_id if run else None,
                                    span_id=req.span_id, event_type="security", category=blocking_violation.rule_id,
                                    severity=blocking_violation.severity, reason=blocking_violation.description))
        await session.commit()
        return InterceptResponse(allowed=False, rule_id=blocking_violation.rule_id,
                                 reason=blocking_violation.description,
                                 violations=[v.model_dump() for v in violations], status="blocked")

    requires_approval = req.tool_name.lower() in settings.approval_tools or bool(req.attributes.get("agentq.requires_approval"))
    if requires_approval:
        approval = (await session.execute(select(ApprovalRequest).where(
            ApprovalRequest.trace_id == req.trace_id, ApprovalRequest.span_id == req.span_id,
            ApprovalRequest.tool_name == req.tool_name
        ))).scalars().first()
        if approval is None:
            approval = ApprovalRequest(trace_id=req.trace_id, agent_run_id=run.agent_run_id if run else None,
                                       span_id=req.span_id, tool_name=req.tool_name,
                                       context=redact(req.attributes), status="pending")
            session.add(approval)
            await session.commit()
            await session.refresh(approval)
        if approval.status != "approved":
            status = "requires_human_review" if approval.status == "pending" else "blocked"
            if run:
                run.status, run.terminal_reason = status, f"Approval {approval.status} for {req.tool_name}"
                await session.commit()
            return InterceptResponse(allowed=False, rule_id="human_approval", reason=f"Approval {approval.status}",
                                     violations=[v.model_dump() for v in violations],
                                     approval_request_id=approval.id, status=status)

    return InterceptResponse(allowed=True, violations=[v.model_dump() for v in violations], status="success")
