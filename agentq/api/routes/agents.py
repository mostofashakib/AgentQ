from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.db.models import Span, Violation

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents(session: AsyncSession = Depends(get_session)):
    spans = (await session.execute(select(Span))).scalars().all()
    violations = (await session.execute(select(Violation))).scalars().all()
    return _build_agents(spans, violations)


def _build_agents(spans, violations) -> list[dict]:
    agents: dict[str, dict] = {}
    trace_to_service: dict[str, str] = {}

    for s in spans:
        trace_to_service[s.trace_id] = s.service_name
        a = agents.setdefault(s.service_name, {
            "service_name": s.service_name,
            "span_count": 0,
            "first_seen": s.created_at,
            "last_seen": s.created_at,
            "violation_count": 0,
        })
        a["span_count"] += 1
        if s.created_at < a["first_seen"]:
            a["first_seen"] = s.created_at
        if s.created_at > a["last_seen"]:
            a["last_seen"] = s.created_at

    for v in violations:
        service_name = trace_to_service.get(v.trace_id)
        if service_name and service_name in agents:
            agents[service_name]["violation_count"] += 1

    return [
        {**a, "first_seen": a["first_seen"].isoformat(), "last_seen": a["last_seen"].isoformat()}
        for a in agents.values()
    ]
