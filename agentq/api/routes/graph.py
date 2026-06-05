from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.db.models import Span

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
async def get_graph(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Span))
    spans = result.scalars().all()
    return _build_graph(spans)


def _build_graph(spans) -> dict:
    if not spans:
        return {"nodes": [], "edges": []}

    span_map = {s.span_id: s for s in spans}
    nodes: dict[str, dict] = {}
    edges: dict[tuple, dict] = {}

    for s in spans:
        key = f"{s.service_name}/{s.gen_ai_operation or s.name}"
        if key not in nodes:
            nodes[key] = {
                "id": key,
                "service_name": s.service_name,
                "operation": s.gen_ai_operation or s.name,
                "span_count": 0,
                "_total_duration": 0.0,
            }
        nodes[key]["span_count"] += 1
        nodes[key]["_total_duration"] += s.duration_ms

    for s in spans:
        if not s.parent_span_id or s.parent_span_id not in span_map:
            continue
        parent = span_map[s.parent_span_id]
        src = f"{parent.service_name}/{parent.gen_ai_operation or parent.name}"
        dst = f"{s.service_name}/{s.gen_ai_operation or s.name}"
        if src == dst:
            continue
        edge_key = (src, dst)
        if edge_key not in edges:
            edges[edge_key] = {"source": src, "target": dst, "call_count": 0}
        edges[edge_key]["call_count"] += 1

    node_list = []
    for n in nodes.values():
        n["avg_duration_ms"] = n["_total_duration"] / n["span_count"]
        del n["_total_duration"]
        node_list.append(n)

    return {"nodes": node_list, "edges": list(edges.values())}
