from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.db.models import ConnectedAgent, Span, Violation
from agentq.api.security import require_admin, require_viewer
from agentq.agents import create_connection

router = APIRouter(prefix="/api/agents", tags=["agents"], dependencies=[Depends(require_viewer)])


@router.get("")
async def list_agents(session: AsyncSession = Depends(get_session)):
    connections = (await session.execute(
        select(ConnectedAgent).where(ConnectedAgent.enabled.is_(True))
    )).scalars().all()
    spans = (await session.execute(select(Span))).scalars().all()
    violations = (await session.execute(select(Violation))).scalars().all()
    stats = {item["service_name"]: item for item in _build_agents(spans, violations)}
    return [{
        "service_name": connection.service_name,
        "capture_traces": connection.capture_traces,
        "analyze_behavior": connection.analyze_behavior,
        "span_count": stats.get(connection.service_name, {}).get("span_count", 0),
        "violation_count": stats.get(connection.service_name, {}).get("violation_count", 0),
        "first_seen": stats.get(connection.service_name, {}).get("first_seen"),
        "last_seen": stats.get(connection.service_name, {}).get("last_seen"),
    } for connection in connections]


class AgentConnectionRequest(BaseModel):
    service_name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    capture_traces: bool = True

    model_config = {"extra": "forbid"}


@router.post("", status_code=status.HTTP_201_CREATED)
async def connect_agent(
    body: AgentConnectionRequest,
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_admin),
):
    agent, token = await create_connection(
        session,
        service_name=body.service_name,
        capture_traces=body.capture_traces,
    )
    return {
        "service_name": agent.service_name,
        "capture_traces": agent.capture_traces,
        "analyze_behavior": agent.analyze_behavior,
        "connection_token": token,
    }


@router.delete("/{service_name}")
async def disconnect_agent(
    service_name: str,
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_admin),
):
    result = await session.execute(delete(ConnectedAgent).where(ConnectedAgent.service_name == service_name))
    await session.commit()
    if not result.rowcount:
        raise HTTPException(status_code=404, detail="Connected agent not found")
    return {"disconnected": service_name}


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
