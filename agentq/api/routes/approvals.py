from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.engine import get_session
from agentq.db.models import AgentRun, ApprovalRequest, MonitoringEvent
from agentq.api.security import Principal, require_admin, require_viewer
from agentq.utils.time import utc_now

router = APIRouter(prefix="/api/approvals", tags=["approvals"], dependencies=[Depends(require_viewer)])


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer_id: str
    reason: str | None = None


def _as_dict(item: ApprovalRequest) -> dict:
    return {"id": item.id, "trace_id": item.trace_id, "agent_run_id": item.agent_run_id,
            "span_id": item.span_id, "tool_name": item.tool_name, "context": item.context,
            "status": item.status, "reviewer_id": item.reviewer_id, "reason": item.reason,
            "created_at": item.created_at.isoformat(),
            "decided_at": item.decided_at.isoformat() if item.decided_at else None}


@router.get("")
async def list_approvals(status: str | None = None, session: AsyncSession = Depends(get_session)):
    stmt = select(ApprovalRequest).order_by(desc(ApprovalRequest.created_at))
    if status:
        stmt = stmt.where(ApprovalRequest.status == status)
    return [_as_dict(item) for item in (await session.execute(stmt)).scalars().all()]


@router.post("/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    body: ApprovalDecision,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_admin),
):
    item = await session.get(ApprovalRequest, approval_id)
    if not item:
        raise HTTPException(404, "Approval request not found")
    if item.status != "pending":
        raise HTTPException(409, "Approval request is already decided")
    reviewer_id = principal.identity if principal.identity != "local-development" else body.reviewer_id
    item.status, item.reviewer_id, item.reason, item.decided_at = body.decision, reviewer_id, body.reason, utc_now()
    run = (await session.execute(select(AgentRun).where(AgentRun.trace_id == item.trace_id))).scalars().first()
    if run:
        run.status = "success" if body.decision == "approved" else "blocked"
        run.terminal_reason = f"Action {body.decision} by reviewer"
    session.add(MonitoringEvent(trace_id=item.trace_id, agent_run_id=item.agent_run_id, span_id=item.span_id,
                                event_type="approval", category=body.decision, severity="high",
                                reason=body.reason or f"Action {body.decision} by {reviewer_id}",
                                metadata_json={"reviewer_id": reviewer_id, "tool_name": item.tool_name}))
    await session.commit()
    await session.refresh(item)
    return _as_dict(item)
