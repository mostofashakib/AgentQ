import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from agentq.api.app import app
from agentq.db.models import BehaviorCluster, BehaviorAssignment
import agentq.db.engine as db_engine_module


async def _seed_cluster(cluster_id: str, name: str = "Behavior-1"):
    async with db_engine_module.async_session() as session:
        session.add(BehaviorCluster(
            id=cluster_id, name=name,
            centroid=[0.1] * 384, trace_count=2,
        ))
        session.add(BehaviorAssignment(
            id=str(uuid.uuid4()), trace_id="trace-a",
            cluster_id=cluster_id, similarity_score=0.95,
        ))
        await session.commit()


async def test_list_behaviors_returns_clusters():
    cid = str(uuid.uuid4())
    await _seed_cluster(cid)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/behaviors")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    cluster = next(c for c in data if c["id"] == cid)
    assert cluster["name"] == "Behavior-1"
    assert cluster["trace_count"] == 2


async def test_get_behavior_returns_detail_and_traces():
    cid = str(uuid.uuid4())
    await _seed_cluster(cid, "My Cluster")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/behaviors/{cid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My Cluster"
    assert len(data["recent_traces"]) == 1
    assert data["recent_traces"][0]["trace_id"] == "trace-a"


async def test_get_behavior_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/behaviors/no-such-id")
    assert resp.status_code == 404


async def test_list_behavior_traces():
    cid = str(uuid.uuid4())
    await _seed_cluster(cid)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/behaviors/{cid}/traces")
    assert resp.status_code == 200
    traces = resp.json()
    assert len(traces) == 1
    assert traces[0]["trace_id"] == "trace-a"
    assert "similarity_score" in traces[0]
