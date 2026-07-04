# agentq/ingest/writer.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.models import Span, SpanRecord
from agentq.events import span_queue, behavior_span_queue
from agentq.config import settings
from agentq.monitoring.redaction import sanitize_span_attributes
from agentq.monitoring.runs import aggregate_run
from agentq.monitoring.logging import log_event


async def write_spans(
    session: AsyncSession, records: list[SpanRecord], *, analyze_behavior: bool = True,
) -> list[Span]:
    spans = []
    for r in records:
        span = Span(
            trace_id=r.trace_id,
            span_id=r.span_id,
            parent_span_id=r.parent_span_id,
            name=r.name,
            span_kind=r.span_kind,
            service_name=r.service_name,
            start_time_unix_nano=r.start_time_unix_nano,
            end_time_unix_nano=r.end_time_unix_nano,
            duration_ms=r.duration_ms,
            status_code=r.status_code,
            gen_ai_system=r.gen_ai_system,
            gen_ai_operation=r.gen_ai_operation,
            gen_ai_input_tokens=r.gen_ai_input_tokens,
            gen_ai_output_tokens=r.gen_ai_output_tokens,
            gen_ai_tool_name=r.gen_ai_tool_name,
            attributes=sanitize_span_attributes(
                r.attributes,
                allow_prompt=settings.environment != "production" and settings.raw_prompt_logging_enabled,
                allow_output=settings.environment != "production" and settings.raw_output_logging_enabled,
            ),
        )
        session.add(span)
        spans.append(span)
        log_event(
            "tool_call" if r.gen_ai_tool_name else "model_call" if r.gen_ai_system else "agent_step",
            trace_id=r.trace_id,
            agent_run_id=None,
            span_id=r.span_id,
            parent_span_id=r.parent_span_id,
            model=r.gen_ai_system,
            tool=r.gen_ai_tool_name,
            latency_ms=r.duration_ms,
            input_tokens=r.gen_ai_input_tokens,
            output_tokens=r.gen_ai_output_tokens,
            status=r.status_code,
        )
    await session.flush()
    for trace_id in {record.trace_id for record in records if record.trace_id}:
        await aggregate_run(session, trace_id)
    await session.commit()
    for r in records:
        await span_queue.put(r)
        if analyze_behavior:
            await behavior_span_queue.put(r)
    return spans
