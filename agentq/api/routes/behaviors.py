# agentq/api/routes/behaviors.py
from __future__ import annotations
import asyncio
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session, async_session
from agentq.db.models import BehaviorCluster, BehaviorAssignment
from agentq.behaviors.rubric import generate_rubric
from agentq.api.security import require_admin

router = APIRouter(prefix="/api/behaviors", tags=["behaviors"])


@router.get("")
async def list_behaviors(
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(BehaviorCluster).order_by(desc(BehaviorCluster.created_at)).limit(limit)
    )
    return [_cluster_to_dict(c) for c in result.scalars().all()]


@router.get("/{cluster_id}")
async def get_behavior(cluster_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(BehaviorCluster).where(BehaviorCluster.id == cluster_id)
    )
    cluster = result.scalars().first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    assignments = (await session.execute(
        select(BehaviorAssignment)
        .where(BehaviorAssignment.cluster_id == cluster_id)
        .order_by(desc(BehaviorAssignment.assigned_at))
        .limit(10)
    )).scalars().all()

    d = _cluster_to_dict(cluster)
    d["recent_traces"] = [
        {"trace_id": a.trace_id, "similarity_score": a.similarity_score}
        for a in assignments
    ]
    return d


@router.post("/{cluster_id}/rubric")
async def trigger_rubric(cluster_id: str, _principal=Depends(require_admin)):
    # Create a new session inside the task — the DI session closes when the route returns
    async def _run() -> None:
        async with async_session() as session:
            await generate_rubric(session, cluster_id)
    asyncio.create_task(_run())
    return {"status": "rubric generation started"}


@router.get("/{cluster_id}/traces")
async def list_behavior_traces(
    cluster_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(BehaviorAssignment)
        .where(BehaviorAssignment.cluster_id == cluster_id)
        .order_by(desc(BehaviorAssignment.assigned_at))
        .offset(offset).limit(limit)
    )
    return [
        {
            "trace_id": a.trace_id,
            "similarity_score": a.similarity_score,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        }
        for a in result.scalars().all()
    ]


def _cluster_to_dict(c: BehaviorCluster) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "rubric": c.rubric,
        "trace_count": c.trace_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
