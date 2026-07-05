import pytest
from httpx import ASGITransport, AsyncClient

from agentq.api.app import app
from agentq.monitoring.similarity import SimilarCallTracker, fingerprint, similar_calls


def test_fingerprint_is_stable_and_order_insensitive():
    a = fingerprint({"x": 1, "y": [1, 2]})
    b = fingerprint({"y": [1, 2], "x": 1})
    assert a == b and len(a) == 16
    assert fingerprint({"x": 2}) != a


def test_record_counts_identical_calls_per_trace():
    tracker = SimilarCallTracker()
    assert tracker.record("t1", "search", {"q": "cats"}) == 1
    assert tracker.record("t1", "search", {"q": "cats"}) == 2
    assert tracker.record("t1", "search", {"q": "dogs"}) == 1      # different args
    assert tracker.record("t2", "search", {"q": "cats"}) == 1      # different trace
    assert tracker.record("t1", "fetch", {"q": "cats"}) == 1       # different tool


def test_reset_clears_trace_state():
    tracker = SimilarCallTracker()
    tracker.record("t1", "search", {"q": "cats"})
    tracker.reset("t1")
    assert tracker.record("t1", "search", {"q": "cats"}) == 1


def test_eviction_bounds_memory():
    tracker = SimilarCallTracker(max_traces=2)
    tracker.record("t1", "a", {})
    tracker.record("t2", "a", {})
    tracker.record("t3", "a", {})   # evicts t1
    assert tracker.record("t1", "a", {}) == 1


@pytest.fixture
async def client(connected_agent_factory):
    token = await connected_agent_factory("agent-a")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-AgentQ-Agent-Token": token}) as value:
        yield value


async def test_intercept_circuit_breaks_on_repeated_identical_arguments(client, monkeypatch):
    from agentq.monitoring import runs

    monkeypatch.setattr(runs.settings, "max_similar_tool_calls", 3)
    similar_calls.reset()

    payload = {
        "resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "agent-a"}}]},
          "scopeSpans": [{"spans": [{"traceId": "similar-trace", "spanId": "root", "name": "agent run", "kind": 2,
            "startTimeUnixNano": "1000000", "endTimeUnixNano": "2000000", "attributes": [],
            "status": {"code": "STATUS_CODE_OK"}}]}]}]
    }
    assert (await client.post("/v1/traces", json=payload)).status_code == 200

    same_args = {
        "trace_id": "similar-trace", "span_id": "call-1", "tool_name": "search_web",
        "service_name": "agent-a", "attributes": {"query": "cats"},
    }
    for _ in range(2):
        resp = (await client.post("/api/intercept", json=same_args)).json()
        assert resp["allowed"] is True

    blocked = (await client.post("/api/intercept", json=same_args)).json()
    assert blocked["allowed"] is False
    assert blocked["rule_id"] == "circuit_breaker"

    different_args = {**same_args, "attributes": {"query": "dogs"}}
    still_allowed = (await client.post("/api/intercept", json=different_args)).json()
    assert still_allowed["allowed"] is True
