import pytest
from httpx import ASGITransport, AsyncClient

from agentq.api.app import app
from agentq.db.models import Span
from agentq.monitoring.cost import is_premium_model
from agentq.monitoring.efficiency import detect_cost_inefficiencies


@pytest.fixture
async def client(connected_agent_factory):
    token = await connected_agent_factory("agent-a")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-AgentQ-Agent-Token": token}) as value:
        yield value


def make_model_span(model="gpt-4o", input_tokens=50, output_tokens=50, fp=None):
    attrs = {"gen_ai.request.model": model}
    if fp:
        attrs["agentq.prompt_fingerprint"] = fp
    return Span(trace_id="t", span_id=f"s{id(attrs)}", name="llm", span_kind="CLIENT",
                service_name="agent", start_time_unix_nano=0, end_time_unix_nano=0, duration_ms=1.0,
                gen_ai_system=model, gen_ai_input_tokens=input_tokens, gen_ai_output_tokens=output_tokens,
                attributes=attrs)


def test_is_premium_model():
    assert is_premium_model("gpt-4o")
    assert is_premium_model("claude-sonnet-4")
    assert not is_premium_model("gpt-4o-mini")
    assert is_premium_model("totally-unknown")  # conservative fallback pricing is premium


def test_repeated_similar_prompts_flagged(monkeypatch):
    from agentq.monitoring import efficiency
    monkeypatch.setattr(efficiency.settings, "max_similar_model_calls", 3)
    spans = [make_model_span(fp="abc123") for _ in range(3)]
    anomalies = detect_cost_inefficiencies(spans)
    assert any(a.category == "repeated_similar_prompts" for a in anomalies)
    assert not any(a.category == "repeated_similar_prompts"
                   for a in detect_cost_inefficiencies(spans[:2]))


def test_expensive_model_for_small_task_flagged(monkeypatch):
    from agentq.monitoring import efficiency
    monkeypatch.setattr(efficiency.settings, "cheap_task_token_threshold", 300)
    small_premium = [make_model_span("gpt-4o", 40, 40)]
    assert any(a.category == "expensive_model_for_small_task"
               for a in detect_cost_inefficiencies(small_premium))
    big_premium = [make_model_span("gpt-4o", 4000, 4000)]
    assert not detect_cost_inefficiencies(big_premium)
    small_cheap = [make_model_span("gpt-4o-mini", 40, 40)]
    assert not detect_cost_inefficiencies(small_cheap)


def test_no_model_spans_is_quiet():
    assert detect_cost_inefficiencies([]) == []


async def test_ingest_stamps_prompt_fingerprint_without_content(client):
    from sqlalchemy import select
    import agentq.db.engine as db_engine
    from agentq.db.models import Span as SpanRow
    payload = {
        "resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "agent-a"}}]},
          "scopeSpans": [{"spans": [{"traceId": "fp-trace", "spanId": "m1", "name": "llm", "kind": 3,
            "startTimeUnixNano": "1000000", "endTimeUnixNano": "2000000", "attributes": [
              {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
              {"key": "gen_ai.prompt", "value": {"stringValue": "summarize the report"}},
            ], "status": {"code": "STATUS_CODE_OK"}}]}]}]
    }
    assert (await client.post("/v1/traces", json=payload)).status_code == 200
    async with db_engine.async_session() as session:
        span = (await session.execute(select(SpanRow).where(SpanRow.span_id == "m1"))).scalars().one()
    assert span.attributes["gen_ai.prompt"] == "[OMITTED]"
    assert len(span.attributes["agentq.prompt_fingerprint"]) == 16
