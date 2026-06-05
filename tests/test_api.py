import pytest
from httpx import AsyncClient, ASGITransport
from agentq.api.app import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_list_traces_empty(client):
    r = await client.get("/api/traces")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_list_violations_empty(client):
    r = await client.get("/api/violations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_ingest_json(client):
    payload = {
        "resourceSpans": [{
            "resource": {"attributes": [
                {"key": "service.name", "value": {"stringValue": "test-agent"}}
            ]},
            "scopeSpans": [{"spans": [{
                "traceId": "trace001",
                "spanId": "span001",
                "name": "chat claude",
                "kind": 3,
                "startTimeUnixNano": "1000000000000",
                "endTimeUnixNano": "1001000000000",
                "attributes": [
                    {"key": "gen_ai.system", "value": {"stringValue": "anthropic"}},
                ],
                "status": {"code": "STATUS_CODE_OK"},
            }]}]
        }]
    }
    r = await client.post("/v1/traces", json=payload)
    assert r.status_code == 200
    assert r.json()["accepted"] == 1


async def test_ingest_protobuf_rejected(client):
    r = await client.post(
        "/v1/traces",
        content=b"\x00\x01",
        headers={"content-type": "application/x-protobuf"},
    )
    assert r.status_code == 415


async def test_traces_after_ingest(client):
    payload = {
        "resourceSpans": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "svc"}}]},
            "scopeSpans": [{"spans": [{
                "traceId": "t999", "spanId": "s999", "name": "op",
                "kind": 2, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000",
                "attributes": [], "status": {},
            }]}]
        }]
    }
    await client.post("/v1/traces", json=payload)
    r = await client.get("/api/traces")
    assert r.status_code == 200
    trace_ids = [s["trace_id"] for s in r.json()]
    assert "t999" in trace_ids
