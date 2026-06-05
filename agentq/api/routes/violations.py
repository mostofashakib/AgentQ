from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.db.models import Violation

router = APIRouter(prefix="/api/violations", tags=["violations"])


@router.get("")
async def list_violations(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    threat_class: str | None = Query(None),
    severity: str | None = Query(None),
    trace_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Violation).order_by(desc(Violation.created_at)).offset(offset).limit(limit)
    if threat_class:
        stmt = stmt.where(Violation.threat_class == threat_class)
    if severity:
        stmt = stmt.where(Violation.severity == severity)
    if trace_id:
        stmt = stmt.where(Violation.trace_id == trace_id)
    result = await session.execute(stmt)
    return [_v_to_dict(v) for v in result.scalars().all()]


def _v_to_dict(v: Violation) -> dict:
    return {
        "id": v.id,
        "trace_id": v.trace_id,
        "span_id": v.span_id,
        "rule_id": v.rule_id,
        "threat_class": v.threat_class,
        "severity": v.severity,
        "blocked": v.blocked,
        "description": v.description,
        "evidence": v.evidence,
        "chain_span_ids": v.chain_span_ids,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }
