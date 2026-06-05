import pytest
import numpy as np
import uuid
from agentq.db.models import BehaviorCluster


def _unit_vec(dim=384, hot_idx=0) -> list[float]:
    v = np.zeros(dim)
    v[hot_idx] = 1.0
    return v.tolist()


async def test_first_trace_creates_new_cluster():
    from agentq.behaviors.clusterer import assign
    from agentq.db.engine import async_session
    from sqlalchemy import select

    vec = _unit_vec(hot_idx=0)
    async with async_session() as session:
        cluster, assignment, is_new = await assign(session, "trace-1", vec)

    assert is_new is True
    assert cluster.name == "Behavior-1"
    assert cluster.trace_count == 1
    assert assignment.trace_id == "trace-1"
    assert assignment.similarity_score == pytest.approx(1.0)


async def test_similar_trace_joins_existing_cluster():
    from agentq.behaviors.clusterer import assign
    from agentq.db.engine import async_session

    vec_a = _unit_vec(hot_idx=0)
    vec_b = np.zeros(384)
    vec_b[0] = 0.9999; vec_b[1] = 0.01
    vec_b = (vec_b / np.linalg.norm(vec_b)).tolist()

    async with async_session() as session:
        cluster_a, _, _ = await assign(session, "trace-1", vec_a)
    async with async_session() as session:
        cluster_b, _, is_new = await assign(session, "trace-2", vec_b)

    assert is_new is False
    assert cluster_a.id == cluster_b.id
    assert cluster_b.trace_count == 2


async def test_orthogonal_trace_creates_new_cluster():
    from agentq.behaviors.clusterer import assign
    from agentq.db.engine import async_session

    vec_a = _unit_vec(hot_idx=0)
    vec_b = _unit_vec(hot_idx=383)  # orthogonal — cosine sim = 0.0

    async with async_session() as session:
        _, _, new_a = await assign(session, "trace-1", vec_a)
    async with async_session() as session:
        cluster_b, _, new_b = await assign(session, "trace-2", vec_b)

    assert new_a is True
    assert new_b is True
    assert cluster_b.name == "Behavior-2"


async def test_centroid_updates_as_running_average():
    from agentq.behaviors.clusterer import assign
    from agentq.db.engine import async_session

    vec_a = _unit_vec(hot_idx=0)
    vec_b = np.zeros(384); vec_b[0] = 0.9999; vec_b[1] = 0.01
    vec_b = (vec_b / np.linalg.norm(vec_b)).tolist()

    async with async_session() as session:
        cluster_a, _, _ = await assign(session, "t1", vec_a)
    async with async_session() as session:
        cluster_b, _, _ = await assign(session, "t2", vec_b)

    # Centroid should no longer equal the original unit vec exactly
    original = np.array(vec_a)
    centroid = np.array(cluster_b.centroid)
    assert not np.allclose(original, centroid, atol=1e-4)
