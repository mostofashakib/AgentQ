from typing import Any
from agentq.db.models import SpanRecord
from agentq.guardrails.registry import build_engine
from agentq.guardrails.models import ViolationRecord

_engine = build_engine()


async def check_action(
    trace_id: str,
    span_id: str,
    tool_name: str,
    service_name: str = "unknown",
    attributes: dict[str, Any] | None = None,
) -> list[ViolationRecord]:
    synthetic = SpanRecord(
        trace_id=trace_id,
        span_id=span_id,
        name=f"tool:{tool_name}",
        span_kind="CLIENT",
        service_name=service_name,
        start_time_unix_nano=0,
        end_time_unix_nano=0,
        duration_ms=0.0,
        gen_ai_tool_name=tool_name,
        attributes={**(attributes or {}), "gen_ai.tool.name": tool_name},
    )
    return await _engine.run_all(synthetic)
