import uuid
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
import agentq.db.engine as _db_engine
from agentq.db.models import Violation, Span
from agentq.guardrails.intercept import check_action as _check_action
from agentq.ingest.simple_report import build_span_record_from_report
from agentq.ingest.writer import write_spans
from agentq.agents import authorize_agent


# streamable_http_path="/" — this app is mounted at /mcp in agentq/api/app.py.
# FastMCP's default streamable_http_path is itself "/mcp", so without this
# override the reachable endpoint would be the doubled "/mcp/mcp".
mcp = FastMCP("agentq", streamable_http_path="/")


@mcp.tool()
async def report_action(
    agent_name: str, tool_name: str, connection_token: str, input: str = "", output: str = "",
) -> dict:
    """Log a completed agent action (a tool call or LLM turn) to AgentQ."""
    record = build_span_record_from_report(
        agent_name=agent_name, tool_name=tool_name, input=input, output=output,
    )
    async with _db_engine.async_session() as session:
        agent = await authorize_agent(session, {agent_name}, connection_token)
        if agent is None:
            return {"accepted": False, "error": "Agent is not connected or its token is invalid"}
        await write_spans(session, [record], analyze_behavior=True)
    return {"accepted": True, "trace_id": record.trace_id, "span_id": record.span_id}


@mcp.tool()
async def check_action(agent_name: str, tool_name: str, attributes: dict | None = None) -> dict:
    """Check a planned action against AgentQ's guardrails before executing it."""
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    violations = await _check_action(
        trace_id=trace_id, span_id=span_id, tool_name=tool_name,
        service_name=agent_name, attributes=attributes,
    )
    return {
        "allowed": True,
        "violations": [v.model_dump() for v in violations],
    }


@mcp.tool()
async def get_violations(agent_name: str, connection_token: str, limit: int = 20) -> dict:
    """Get recent guardrail violations for a given agent (service_name)."""
    async with _db_engine.async_session() as session:
        agent = await authorize_agent(session, {agent_name}, connection_token)
        if agent is None:
            return {"violations": [], "error": "Agent is not connected or its token is invalid"}
        trace_ids = (
            await session.execute(
                select(Span.trace_id).where(Span.service_name == agent_name).distinct()
            )
        ).scalars().all()
        if not trace_ids:
            return {"violations": []}
        rows = (
            await session.execute(
                select(Violation)
                .where(Violation.trace_id.in_(trace_ids))
                .order_by(Violation.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    return {
        "violations": [
            {
                "trace_id": v.trace_id,
                "rule_id": v.rule_id,
                "threat_class": v.threat_class,
                "severity": v.severity,
                "description": v.description,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in rows
        ]
    }
