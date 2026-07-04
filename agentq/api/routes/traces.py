from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.db.models import Span
from agentq.api.security import require_viewer
from agentq.db.visibility import visible_spans

router = APIRouter(prefix="/api/traces", tags=["traces"], dependencies=[Depends(require_viewer)])


@router.get("")
async def list_traces(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    stmt = visible_spans().order_by(desc(Span.start_time_unix_nano)).offset(offset).limit(limit)
    if service:
        stmt = stmt.where(Span.service_name == service)
    result = await session.execute(stmt)
    spans = result.scalars().all()
    return [_span_to_dict(s) for s in spans]


@router.get("/{trace_id}/waterfall")
async def get_trace_waterfall(trace_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        visible_spans()
        .where(Span.trace_id == trace_id)
        .order_by(Span.start_time_unix_nano)
    )
    spans = result.scalars().all()
    return _build_waterfall(spans)


def _build_waterfall(spans) -> list[dict]:
    if not spans:
        return []
    span_ids = {s.span_id for s in spans}
    nodes: dict[str, dict] = {}
    for s in spans:
        d = _span_to_dict(s)
        d["children"] = []
        d["depth"] = 0
        nodes[s.span_id] = d

    roots = []
    for s in spans:
        node = nodes[s.span_id]
        if s.parent_span_id and s.parent_span_id in span_ids:
            nodes[s.parent_span_id]["children"].append(node)
        else:
            roots.append(node)

    def _set_depth(node: dict, depth: int) -> None:
        node["depth"] = depth
        for child in node["children"]:
            _set_depth(child, depth + 1)

    for root in roots:
        _set_depth(root, 0)

    return roots


@router.get("/{trace_id}")
async def get_trace(trace_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(visible_spans().where(Span.trace_id == trace_id))
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
