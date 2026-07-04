async def test_report_action_creates_span(connected_agent_factory):
    from agentq.mcp.server import report_action
    import agentq.db.engine as _db_engine
    from sqlalchemy import select
    from agentq.db.models import Span

    token = await connected_agent_factory("mcp-test-agent")
    result = await report_action(
        agent_name="mcp-test-agent", tool_name="search_web",
        connection_token=token,
        input="query=weather", output="sunny",
    )
    assert result["accepted"] is True
    assert result["trace_id"]

    async with _db_engine.async_session() as session:
        rows = (await session.execute(
            select(Span).where(Span.service_name == "mcp-test-agent")
        )).scalars().all()
    assert len(rows) == 1
    assert rows[0].gen_ai_tool_name == "search_web"


async def test_check_action_returns_violations():
    from agentq.mcp.server import check_action as mcp_check_action

    result = await mcp_check_action(agent_name="mcp-test-agent", tool_name="exec_command")
    rule_ids = [v["rule_id"] for v in result["violations"]]
    assert "scope.high_risk_tool" in rule_ids


async def test_get_violations_returns_violations_for_agent(connected_agent_factory):
    from agentq.mcp.server import report_action as mcp_report_action, get_violations as mcp_get_violations
    from agentq.api.worker import _save_violations
    from agentq.guardrails.registry import build_engine
    import agentq.db.engine as _db_engine
    from sqlalchemy import select
    from agentq.db.models import Span

    token = await connected_agent_factory("mcp-violations-agent")
    await mcp_report_action(
        agent_name="mcp-violations-agent", tool_name="exec_command",
        connection_token=token,
        input="rm -rf /", output="",
    )
    async with _db_engine.async_session() as session:
        span_row = (await session.execute(
            select(Span).where(Span.service_name == "mcp-violations-agent")
        )).scalars().first()

    from agentq.db.models import SpanRecord
    engine = build_engine()
    synthetic = SpanRecord(
        trace_id=span_row.trace_id, span_id=span_row.span_id, name=span_row.name,
        span_kind=span_row.span_kind, service_name=span_row.service_name,
        start_time_unix_nano=0, end_time_unix_nano=0, duration_ms=0.0,
        gen_ai_tool_name=span_row.gen_ai_tool_name, attributes=span_row.attributes,
    )
    violations = await engine.run_all(synthetic)
    await _save_violations(violations)

    result = await mcp_get_violations(
        agent_name="mcp-violations-agent", connection_token=token, limit=10,
    )
    assert len(result["violations"]) >= 1
    assert result["violations"][0]["trace_id"] == span_row.trace_id


async def test_get_violations_empty_for_unknown_agent():
    from agentq.mcp.server import get_violations as mcp_get_violations

    result = await mcp_get_violations(
        agent_name="no-such-agent", connection_token="invalid", limit=10,
    )
    assert result["violations"] == []
