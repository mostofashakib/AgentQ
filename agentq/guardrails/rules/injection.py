import re
from agentq.db.models import SpanRecord
from agentq.guardrails.models import ViolationRecord
from agentq.guardrails.utils.pattern_match import find_injection, find_role_confusion

_RETRIEVAL_TOOLS = {"search", "retrieve", "get_document", "web_search", "lookup", "query_db"}


async def user_content_injection(span: SpanRecord) -> list[ViolationRecord]:
    text = span.attributes.get("gen_ai.prompt", "")
    if not isinstance(text, str):
        return []
    evidence = find_injection(text)
    if not evidence:
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="injection.user_content",
        threat_class="injection", severity="high", blocked=True,
        description="User message contains prompt injection pattern",
        evidence=evidence[:300],
    )]


async def system_prompt_override(span: SpanRecord) -> list[ViolationRecord]:
    text = span.attributes.get("gen_ai.tool.result", "")
    if not isinstance(text, str):
        return []
    if re.search(r"<\s*/?system\s*>|system\s*prompt\s*[:=]", text, re.IGNORECASE):
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="injection.system_prompt_override",
            threat_class="injection", severity="critical", blocked=True,
            description="Tool output attempts to override system prompt",
            evidence=text[:300],
        )]
    return []


async def indirect_injection_via_retrieval(span: SpanRecord) -> list[ViolationRecord]:
    if span.gen_ai_tool_name not in _RETRIEVAL_TOOLS:
        return []
    text = span.attributes.get("gen_ai.tool.result", "")
    if not isinstance(text, str):
        return []
    evidence = find_injection(text)
    if not evidence:
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="injection.indirect_via_retrieval",
        threat_class="injection", severity="high", blocked=False,
        description="Retrieved content contains prompt injection attempt",
        evidence=evidence[:300],
    )]


async def role_confusion_attack(span: SpanRecord) -> list[ViolationRecord]:
    text = span.attributes.get("gen_ai.prompt", "")
    if not isinstance(text, str):
        return []
    evidence = find_role_confusion(text)
    if not evidence:
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="injection.role_confusion",
        threat_class="injection", severity="medium", blocked=False,
        description="Prompt contains role confusion / persona hijack attempt",
        evidence=evidence,
    )]
