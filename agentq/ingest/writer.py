# agentq/ingest/writer.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.models import Span, SpanRecord
from agentq.events import span_queue, behavior_span_queue


async def write_spans(session: AsyncSession, records: list[SpanRecord]) -> list[Span]:
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
            attributes=r.attributes,
        )
        session.add(span)
        spans.append(span)
    await session.commit()
    for r in records:
        await span_queue.put(r)
        await behavior_span_queue.put(r)
    return spans
