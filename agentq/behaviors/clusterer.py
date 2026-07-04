from __future__ import annotations
import uuid
from datetime import datetime
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.models import BehaviorCluster, BehaviorAssignment
from agentq.guardrails.settings import get_app_settings


def _cosine_sim(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


async def assign(
    session: AsyncSession,
    trace_id: str,
    vector: list[float],
) -> tuple[BehaviorCluster, BehaviorAssignment, bool]:
    result = await session.execute(select(BehaviorCluster))
    clusters = result.scalars().all()

    best_cluster: BehaviorCluster | None = None
    best_sim = 0.0
    for c in clusters:
        if not c.centroid:
            continue
        sim = _cosine_sim(vector, c.centroid)
        if sim > best_sim:
            best_sim = sim
            best_cluster = c

    threshold = (await get_app_settings()).behavior_similarity_threshold
    is_new = best_cluster is None or best_sim < threshold

    if is_new:
        best_cluster = BehaviorCluster(
            id=str(uuid.uuid4()),
            name=f"Behavior-{len(clusters) + 1}",
            centroid=vector,
            trace_count=1,
        )
        session.add(best_cluster)
        best_sim = 1.0
    else:
        n = best_cluster.trace_count + 1
        old = np.array(best_cluster.centroid)
        new_centroid = (old * (n - 1) + np.array(vector)) / n
        norm = float(np.linalg.norm(new_centroid))
        best_cluster.centroid = (new_centroid / norm).tolist() if norm > 0 else new_centroid.tolist()
        best_cluster.trace_count = n

    assignment = BehaviorAssignment(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        cluster_id=best_cluster.id,
        similarity_score=best_sim,
        assigned_at=datetime.utcnow(),
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(best_cluster)
    return best_cluster, assignment, is_new
