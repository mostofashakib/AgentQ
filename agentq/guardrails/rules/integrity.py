from agentq.db.models import SpanRecord
from agentq.guardrails.models import ViolationRecord


async def span_time_inversion(span: SpanRecord) -> list[ViolationRecord]:
    if span.end_time_unix_nano <= span.start_time_unix_nano:
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="integrity.time_inversion",
            threat_class="integrity", severity="low",
            description="Span end time is not after start time",
            evidence=f"start={span.start_time_unix_nano} end={span.end_time_unix_nano}",
        )]
    return []


async def missing_service_name(span: SpanRecord) -> list[ViolationRecord]:
    if span.service_name in ("unknown", "", None):
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="integrity.missing_service_name",
            threat_class="integrity", severity="low",
            description="Span is missing a service.name resource attribute",
        )]
    return []


async def model_call_missing_gen_ai_attrs(span: SpanRecord) -> list[ViolationRecord]:
    if span.span_kind != "CLIENT":
        return []
    if span.gen_ai_system or span.gen_ai_operation:
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="integrity.missing_gen_ai_attrs",
        threat_class="integrity", severity="low",
        description="CLIENT span is missing gen_ai.system and gen_ai.operation.name attributes",
    )]


async def empty_trace_id(span: SpanRecord) -> list[ViolationRecord]:
    if not span.trace_id or span.trace_id.strip() == "":
        return [ViolationRecord(
            trace_id=span.trace_id or "MISSING",
            span_id=span.span_id,
            rule_id="integrity.empty_trace_id",
            threat_class="integrity", severity="medium",
            description="Span has an empty or missing trace_id",
        )]
    return []
