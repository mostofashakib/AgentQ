import time
import uuid
from agentq.db.models import SpanRecord


def build_span_record_from_report(
    agent_name: str,
    tool_name: str,
    input: str = "",
    output: str = "",
    attributes: dict | None = None,
) -> SpanRecord:
    now_ns = time.time_ns()
    attrs = {**(attributes or {}), "gen_ai.tool.name": tool_name}
    if input:
        attrs["gen_ai.tool.call.arguments"] = input
    if output:
        attrs["gen_ai.tool.result"] = output
    return SpanRecord(
        trace_id=uuid.uuid4().hex,
        span_id=uuid.uuid4().hex[:16],
        name=f"tool:{tool_name}",
        span_kind="CLIENT",
        service_name=agent_name,
        start_time_unix_nano=now_ns,
        end_time_unix_nano=now_ns,
        duration_ms=0.0,
        gen_ai_tool_name=tool_name,
        attributes=attrs,
    )
