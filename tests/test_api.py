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


async def test_ingest_protobuf_accepted(client):
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )
    from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

    def kv(key, **value_kwargs):
        return KeyValue(key=key, value=AnyValue(**value_kwargs))

    span = Span(
        trace_id=b"\x01" * 16, span_id=b"\x02" * 8, name="chat claude",
        kind=Span.SPAN_KIND_CLIENT,
        start_time_unix_nano=1_000_000_000_000, end_time_unix_nano=1_000_100_000_000,
        attributes=[kv("gen_ai.system", string_value="anthropic")],
    )
    resource_spans = ResourceSpans(
        resource=Resource(attributes=[kv("service.name", string_value="test-agent")]),
        scope_spans=[ScopeSpans(spans=[span])],
    )
    body = ExportTraceServiceRequest(resource_spans=[resource_spans]).SerializeToString()

    r = await client.post(
        "/v1/traces",
        content=body,
        headers={"content-type": "application/x-protobuf"},
    )
    assert r.status_code == 200
    assert r.json()["accepted"] == 1


async def test_ingest_protobuf_malformed_body_400(client):
    r = await client.post(
        "/v1/traces",
        content=b"\xff\xff\xff\xff\xff\xff\xff\xff\xff",
        headers={"content-type": "application/x-protobuf"},
    )
    assert r.status_code == 400


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
