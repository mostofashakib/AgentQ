# agentq/behaviors/worker.py
from __future__ import annotations
import asyncio
import logging
from agentq.db.models import SpanRecord
from agentq.events import behavior_span_queue, alert_event_queue, BehaviorAlertEvent
from agentq.behaviors.embedder import compute_composite
from agentq.behaviors import clusterer
from agentq.behaviors import rubric as rubric_gen
from agentq.db.engine import async_session

logger = logging.getLogger(__name__)

_FLUSH_DELAY: float = 5.0
_trace_buffer: dict[str, list[SpanRecord]] = {}
_flush_tasks: dict[str, asyncio.Task] = {}


async def _flush_trace(trace_id: str) -> None:
    await asyncio.sleep(_FLUSH_DELAY)
    spans = _trace_buffer.pop(trace_id, [])
    _flush_tasks.pop(trace_id, None)
    if not spans:
        return

    try:
        vector = compute_composite(spans)

        async with async_session() as session:
            cluster, assignment, _ = await clusterer.assign(session, trace_id, vector)
            should_generate_rubric = cluster.trace_count == 10 and not cluster.rubric
            cluster_id = cluster.id

        if should_generate_rubric:
            asyncio.create_task(_run_rubric(cluster_id))

        await alert_event_queue.put(BehaviorAlertEvent(
            cluster_id=cluster_id,
            trace_id=trace_id,
            similarity_score=assignment.similarity_score,
        ))
    except Exception:
        logger.exception("behavior_worker error flushing trace %s", trace_id)


async def _run_rubric(cluster_id: str) -> None:
    try:
        async with async_session() as session:
            await rubric_gen.generate_rubric(session, cluster_id)
    except Exception:
        logger.exception("rubric generation failed for cluster %s", cluster_id)


async def behavior_worker() -> None:
    while True:
        span = await behavior_span_queue.get()
        try:
            trace_id = span.trace_id
            _trace_buffer.setdefault(trace_id, []).append(span)

            existing = _flush_tasks.get(trace_id)
            if existing and not existing.done():
                existing.cancel()
            _flush_tasks[trace_id] = asyncio.create_task(_flush_trace(trace_id))
        except Exception:
            logger.exception("behavior_worker error handling span %s", span.span_id)
        finally:
            behavior_span_queue.task_done()
