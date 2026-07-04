async def test_build_span_record_from_report_basic():
    from agentq.ingest.simple_report import build_span_record_from_report

    record = build_span_record_from_report(
        agent_name="my-agent", tool_name="send_email",
        input="to: a@b.com", output="sent",
    )
    assert record.service_name == "my-agent"
    assert record.gen_ai_tool_name == "send_email"
    assert record.name == "tool:send_email"
    assert record.span_kind == "CLIENT"
    assert record.attributes["gen_ai.tool.call.arguments"] == "to: a@b.com"
    assert record.attributes["gen_ai.tool.result"] == "sent"
    assert record.trace_id and record.span_id


async def test_build_span_record_from_report_no_input_output():
    from agentq.ingest.simple_report import build_span_record_from_report

    record = build_span_record_from_report(agent_name="my-agent", tool_name="ping")
    assert "gen_ai.tool.call.arguments" not in record.attributes
    assert "gen_ai.tool.result" not in record.attributes


from httpx import AsyncClient, ASGITransport
from agentq.api.app import app


async def test_report_endpoint_creates_span_and_returns_ids(connected_agent_factory):
    token = await connected_agent_factory("report-test-agent")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-AgentQ-Agent-Token": token}) as client:
        r = await client.post("/api/report", json={
            "agent_name": "report-test-agent",
            "tool_name": "search_web",
            "input": "query=cats",
            "output": "12 results",
        })
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["trace_id"]
    assert body["span_id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        traces = (await client.get("/api/traces", params={"service": "report-test-agent"})).json()
    assert any(t["trace_id"] == body["trace_id"] for t in traces)
