from agentq.db.models import SpanRecord
from agentq.guardrails.models import ViolationRecord
from agentq.guardrails.utils.pattern_match import is_high_risk_tool
from agentq.guardrails.settings import get_app_settings

_DESTRUCTIVE_VERBS = {"delete", "drop", "remove", "destroy", "purge", "wipe", "format", "truncate"}


async def high_risk_tool_call(span: SpanRecord) -> list[ViolationRecord]:
    tool = span.gen_ai_tool_name
    if not tool or not is_high_risk_tool(tool):
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="scope.high_risk_tool",
        threat_class="scope", severity="high",
        description=f"High-risk tool invoked: {tool}",
        evidence=tool,
    )]


async def unsanctioned_external_call(span: SpanRecord) -> list[ViolationRecord]:
    allowed: list[str] = span.attributes.get("agentq.allowed_tools", []) or []
    tool = span.gen_ai_tool_name
    if not tool or not allowed:
        return []
    if tool not in allowed:
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="scope.unsanctioned_tool",
            threat_class="scope", severity="medium",
            description=f"Tool '{tool}' is not in the declared allowed list",
            evidence=f"allowed={allowed}",
        )]
    return []


async def excessive_tool_calls(span: SpanRecord) -> list[ViolationRecord]:
    call_count = span.attributes.get("agentq.trace_tool_call_count", 0)
    threshold = (await get_app_settings()).excessive_tool_calls_threshold
    if isinstance(call_count, int) and call_count > threshold:
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="scope.excessive_tool_calls",
            threat_class="scope", severity="medium",
            description=f"Trace has {call_count} tool calls, exceeding limit of {threshold}",
            evidence=str(call_count),
        )]
    return []


async def destructive_action_without_confirmation(span: SpanRecord) -> list[ViolationRecord]:
    tool = (span.gen_ai_tool_name or "").lower()
    if not any(v in tool for v in _DESTRUCTIVE_VERBS):
        return []
    confirmed = span.attributes.get("agentq.user_confirmed", False)
    if confirmed:
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="scope.destructive_without_confirmation",
        threat_class="scope", severity="critical",
        description=f"Destructive tool '{tool}' invoked without user confirmation",
        evidence=tool,
    )]
