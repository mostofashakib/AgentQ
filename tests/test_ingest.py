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
