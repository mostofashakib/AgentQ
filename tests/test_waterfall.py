import pytest
from httpx import AsyncClient, ASGITransport
from agentq.api.app import app

PARENT_CHILD_PAYLOAD = {
    "resourceSpans": [{
        "resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": "agent"}}
        ]},
        "scopeSpans": [{"spans": [
            {
                "traceId": "trace001",
                "spanId": "root001",
                "parentSpanId": "",
                "name": "root-span",
                "kind": 1,
                "startTimeUnixNano": "1000000000",
                "endTimeUnixNano": "5000000000",
                "attributes": [],
                "status": {},
            },
            {
                "traceId": "trace001",
                "spanId": "child001",
                "parentSpanId": "root001",
                "name": "child-span",
                "kind": 3,
                "startTimeUnixNano": "2000000000",
                "endTimeUnixNano": "4000000000",
                "attributes": [],
                "status": {},
            },
        ]}]
    }]
}


async def test_waterfall_returns_tree_structure(connected_agent_factory):
    token = await connected_agent_factory("agent")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-AgentQ-Agent-Token": token}) as client:
        ingest = await client.post("/v1/traces", json=PARENT_CHILD_PAYLOAD)
        assert ingest.json()["accepted"] == 2

        resp = await client.get("/api/traces/trace001/waterfall")
        assert resp.status_code == 200
        tree = resp.json()

    assert len(tree) == 1
    root = tree[0]
    assert root["span_id"] == "root001"
    assert root["depth"] == 0
    assert len(root["children"]) == 1

    child = root["children"][0]
    assert child["span_id"] == "child001"
    assert child["depth"] == 1
    assert child["children"] == []


async def test_waterfall_empty_trace_returns_empty_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/traces/nonexistent/waterfall")
    assert resp.status_code == 200
    assert resp.json() == []
