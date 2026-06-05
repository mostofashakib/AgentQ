from agentq.db.models import SpanRecord
from agentq.guardrails.models import ViolationRecord

_TOKEN_EXPLOSION_THRESHOLD = 8000


async def goal_drift(span: SpanRecord) -> list[ViolationRecord]:
    original_goal = span.attributes.get("agentq.original_goal", "")
    current_task = span.attributes.get("agentq.current_task", "")
    if not original_goal or not current_task:
        return []
    if original_goal.lower().strip() != current_task.lower().strip():
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="behavioral.goal_drift",
            threat_class="behavioral", severity="medium",
            description="Agent task objective has drifted from original goal",
            evidence=f"original='{original_goal[:100]}' current='{current_task[:100]}'",
        )]
    return []


async def infinite_loop_detection(span: SpanRecord) -> list[ViolationRecord]:
    seen_names: list[str] = span.attributes.get("agentq.trace_span_names", [])
    if not isinstance(seen_names, list) or not span.name:
        return []
    occurrences = seen_names.count(span.name)
    if occurrences >= 5:
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="behavioral.infinite_loop",
            threat_class="behavioral", severity="high",
            description=f"Span '{span.name}' has repeated {occurrences} times in this trace",
            evidence=f"name='{span.name}' count={occurrences}",
        )]
    return []


async def hallucinated_tool(span: SpanRecord) -> list[ViolationRecord]:
    declared_tools: list[str] = span.attributes.get("agentq.declared_tools", []) or []
    tool = span.gen_ai_tool_name
    if not tool or not declared_tools:
        return []
    if tool not in declared_tools:
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="behavioral.hallucinated_tool",
            threat_class="behavioral", severity="high",
            description=f"Agent invoked tool '{tool}' which is not in the declared tool schema",
            evidence=f"tool='{tool}' declared={declared_tools}",
        )]
    return []


async def token_explosion(span: SpanRecord) -> list[ViolationRecord]:
    total = (span.gen_ai_input_tokens or 0) + (span.gen_ai_output_tokens or 0)
    if total > _TOKEN_EXPLOSION_THRESHOLD:
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="behavioral.token_explosion",
            threat_class="behavioral", severity="medium",
            description=f"Span used {total} tokens, exceeding threshold of {_TOKEN_EXPLOSION_THRESHOLD}",
            evidence=f"input={span.gen_ai_input_tokens} output={span.gen_ai_output_tokens}",
        )]
    return []
