from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from agentq.api.app import app
from agentq.db import engine as db_engine
from agentq.db.models import ConnectedAgent, Span
from tests.test_ingest import SAMPLE_PAYLOAD


async def _connect(client: AsyncClient, name: str = "test-agent") -> str:
    response = await client.post("/api/agents", json={
        "service_name": name,
        "capture_traces": True,
    })
    assert response.status_code == 201
    return response.json()["connection_token"]


async def test_unregistered_agent_traces_are_rejected_before_storage():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/traces", json=SAMPLE_PAYLOAD)

    assert response.status_code == 403
    async with db_engine.async_session() as session:
        assert (await session.execute(select(Span))).scalars().all() == []


async def test_connected_agent_requires_matching_connection_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _connect(client)
        rejected = await client.post(
            "/v1/traces", headers={"X-AgentQ-Agent-Token": "wrong"}, json=SAMPLE_PAYLOAD,
        )
        accepted = await client.post(
            "/v1/traces", headers={"X-AgentQ-Agent-Token": token}, json=SAMPLE_PAYLOAD,
        )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json()["accepted"] == 1


async def test_connection_token_is_only_returned_once_and_stored_as_hash():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _connect(client)
        listed = (await client.get("/api/agents")).json()

    assert "connection_token" not in listed[0]
    async with db_engine.async_session() as session:
        agent = (await session.execute(select(ConnectedAgent))).scalar_one()
        assert agent.token_hash != token
        assert len(agent.token_hash) == 64


async def test_disconnected_agent_can_no_longer_ingest():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _connect(client)
        assert (await client.post(
            "/v1/traces", headers={"X-AgentQ-Agent-Token": token}, json=SAMPLE_PAYLOAD,
        )).status_code == 200
        assert (await client.delete("/api/agents/test-agent")).status_code == 200
        response = await client.post(
            "/v1/traces", headers={"X-AgentQ-Agent-Token": token}, json=SAMPLE_PAYLOAD,
        )
        visible_traces = (await client.get("/api/traces")).json()

    assert response.status_code == 403
    assert visible_traces == []


async def test_every_connected_agent_enqueues_behavior_analysis(monkeypatch):
    from agentq.ingest import writer

    queued = []

    async def capture(record):
        queued.append(record)

    monkeypatch.setattr(writer.behavior_span_queue, "put", capture)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _connect(client)
        response = await client.post(
            "/v1/traces", headers={"X-AgentQ-Agent-Token": token}, json=SAMPLE_PAYLOAD,
        )

    assert response.status_code == 200
    assert len(queued) == 1


async def test_multiple_agents_can_be_connected_and_observed_together():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _connect(client, "agent-one")
        await _connect(client, "agent-two")
        connected = (await client.get("/api/agents")).json()

    assert {agent["service_name"] for agent in connected} == {"agent-one", "agent-two"}
    assert all(agent["analyze_behavior"] is True for agent in connected)


async def test_behavior_analysis_cannot_be_disabled():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/agents", json={
            "service_name": "agent-one",
            "capture_traces": True,
            "analyze_behavior": False,
        })

    assert response.status_code == 422
