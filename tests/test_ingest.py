import pytest
from agentq.ingest.parser import parse_otlp_json

SAMPLE_PAYLOAD = {
    "resourceSpans": [{
        "resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": "test-agent"}}
        ]},
        "scopeSpans": [{"spans": [{
            "traceId": "abc123",
            "spanId": "span001",
            "parentSpanId": "",
            "name": "chat claude",
            "kind": 3,
            "startTimeUnixNano": "1000000000000",
            "endTimeUnixNano": "1000100000000",
            "attributes": [
                {"key": "gen_ai.system", "value": {"stringValue": "anthropic"}},
                {"key": "gen_ai.operation.name", "value": {"stringValue": "chat"}},
                {"key": "gen_ai.usage.input_tokens", "value": {"intValue": 150}},
                {"key": "gen_ai.usage.output_tokens", "value": {"intValue": 250}},
                {"key": "gen_ai.response.finish_reasons", "value": {
                    "arrayValue": {"values": [{"stringValue": "stop"}]}
                }},
            ],
            "status": {"code": "STATUS_CODE_OK"},
        }]}]
    }]
}


def test_parse_basic():
    records = parse_otlp_json(SAMPLE_PAYLOAD)
    assert len(records) == 1
    r = records[0]
    assert r.trace_id == "abc123"
    assert r.span_id == "span001"
    assert r.parent_span_id is None
    assert r.span_kind == "CLIENT"
    assert r.service_name == "test-agent"
    assert r.gen_ai_system == "anthropic"
    assert r.gen_ai_input_tokens == 150
    assert r.gen_ai_output_tokens == 250
    assert r.gen_ai_finish_reasons == ["stop"]
    assert r.duration_ms == pytest.approx(100.0)


def test_parse_empty():
    assert parse_otlp_json({}) == []
    assert parse_otlp_json({"resourceSpans": []}) == []


def test_parse_server_span_kind():
    payload = {
        "resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"spans": [{
            "traceId": "t1", "spanId": "s1", "name": "agent-root",
            "kind": 2,
            "startTimeUnixNano": "0", "endTimeUnixNano": "1000000",
            "attributes": [], "status": {},
        }]}]}]
    }
    records = parse_otlp_json(payload)
    assert records[0].span_kind == "SERVER"
    assert records[0].service_name == "unknown"


async def test_write_spans():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from agentq.db.models import Base, SpanRecord
    from agentq.ingest.writer import write_spans

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        records = parse_otlp_json(SAMPLE_PAYLOAD)
        spans = await write_spans(session, records)
    assert len(spans) == 1
    assert spans[0].trace_id == "abc123"


def _build_protobuf_request():
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )
    from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span, Status
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

    def kv(key, **value_kwargs):
        return KeyValue(key=key, value=AnyValue(**value_kwargs))

    span = Span(
        trace_id=bytes.fromhex("0102030405060708090a0b0c0d0e0f10"),
        span_id=bytes.fromhex("0102030405060708"),
        parent_span_id=b"",
        name="chat claude",
        kind=Span.SPAN_KIND_CLIENT,
        start_time_unix_nano=1_000_000_000_000,
        end_time_unix_nano=1_000_100_000_000,
        attributes=[
            kv("gen_ai.system", string_value="anthropic"),
            kv("gen_ai.operation.name", string_value="chat"),
            kv("gen_ai.usage.input_tokens", int_value=150),
            kv("gen_ai.usage.output_tokens", int_value=250),
        ],
        status=Status(code=Status.STATUS_CODE_OK),
    )
    resource_spans = ResourceSpans(
        resource=Resource(attributes=[kv("service.name", string_value="test-agent")]),
        scope_spans=[ScopeSpans(spans=[span])],
    )
    return ExportTraceServiceRequest(resource_spans=[resource_spans]).SerializeToString()


def test_parse_protobuf_basic():
    from agentq.ingest.parser import parse_otlp_protobuf

    body = _build_protobuf_request()
    records = parse_otlp_protobuf(body)
    assert len(records) == 1
    r = records[0]
    assert r.trace_id == "0102030405060708090a0b0c0d0e0f10"
    assert r.span_id == "0102030405060708"
    assert r.parent_span_id is None
    assert r.span_kind == "CLIENT"
    assert r.service_name == "test-agent"
    assert r.gen_ai_system == "anthropic"
    assert r.gen_ai_input_tokens == 150
    assert r.gen_ai_output_tokens == 250
    assert r.status_code == "STATUS_CODE_OK"
    assert r.duration_ms == pytest.approx(100.0)


def test_parse_protobuf_matches_json_for_equivalent_span():
    from agentq.ingest.parser import parse_otlp_protobuf

    json_records = parse_otlp_json(SAMPLE_PAYLOAD)
    proto_records = parse_otlp_protobuf(_build_protobuf_request())
    # Different trace/span IDs by construction (hex vs test string) — compare
    # everything else that both paths must produce identically.
    j, p = json_records[0], proto_records[0]
    assert j.span_kind == p.span_kind
    assert j.service_name == p.service_name
    assert j.gen_ai_system == p.gen_ai_system
    assert j.gen_ai_operation == p.gen_ai_operation
    assert j.duration_ms == pytest.approx(p.duration_ms)


def test_parse_protobuf_mcp_span_normalized():
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )
    from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue
    from agentq.ingest.parser import parse_otlp_protobuf

    def kv(key, **value_kwargs):
        return KeyValue(key=key, value=AnyValue(**value_kwargs))

    span = Span(
        trace_id=b"\x01" * 16,
        span_id=b"\x02" * 8,
        name="tool call",
        kind=Span.SPAN_KIND_CLIENT,
        start_time_unix_nano=0,
        end_time_unix_nano=1_000_000,
        attributes=[
            kv("mcp.server.name", string_value="filesystem"),
            kv("mcp.tool.name", string_value="read_file"),
        ],
    )
    resource_spans = ResourceSpans(
        resource=Resource(attributes=[kv("service.name", string_value="mcp-agent")]),
        scope_spans=[ScopeSpans(spans=[span])],
    )
    body = ExportTraceServiceRequest(resource_spans=[resource_spans]).SerializeToString()

    records = parse_otlp_protobuf(body)
    assert records[0].gen_ai_system == "mcp:filesystem"
    assert records[0].gen_ai_tool_name == "read_file"
