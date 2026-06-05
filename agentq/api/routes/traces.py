from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.db.models import Span

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("")
async def list_traces(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Span).order_by(desc(Span.start_time_unix_nano)).offset(offset).limit(limit)
    if service:
        stmt = stmt.where(Span.service_name == service)
    result = await session.execute(stmt)
    spans = result.scalars().all()
    return [_span_to_dict(s) for s in spans]


@router.get("/{trace_id}")
async def get_trace(trace_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Span).where(Span.trace_id == trace_id))
    spans = result.scalars().all()
    return [_span_to_dict(s) for s in spans]


def _span_to_dict(s: Span) -> dict:
    return {
        "id": s.id,
        "trace_id": s.trace_id,
        "span_id": s.span_id,
        "parent_span_id": s.parent_span_id,
        "name": s.name,
        "span_kind": s.span_kind,
        "service_name": s.service_name,
        "start_time_unix_nano": s.start_time_unix_nano,
        "end_time_unix_nano": s.end_time_unix_nano,
        "duration_ms": s.duration_ms,
        "status_code": s.status_code,
        "gen_ai_system": s.gen_ai_system,
        "gen_ai_operation": s.gen_ai_operation,
        "gen_ai_input_tokens": s.gen_ai_input_tokens,
        "gen_ai_output_tokens": s.gen_ai_output_tokens,
        "gen_ai_tool_name": s.gen_ai_tool_name,
        "attributes": s.attributes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
