import pytest
import asyncio
import uuid
from agentq.db.models import SpanRecord, BehaviorCluster, BehaviorAssignment


async def test_flush_trace_assigns_cluster(monkeypatch):
    from agentq.behaviors import worker as bw
    from agentq.db.engine import async_session
    from sqlalchemy import select

    # Speed up the flush delay
    monkeypatch.setattr(bw, "_FLUSH_DELAY", 0.0)
    bw._trace_buffer.clear()
    bw._flush_tasks.clear()

    span = SpanRecord(
        trace_id="test-trace", span_id=str(uuid.uuid4()),
        name="chat", span_kind="CLIENT", service_name="svc",
        start_time_unix_nano=0, end_time_unix_nano=1_000_000, duration_ms=1.0,
        gen_ai_operation="chat",
        attributes={"gen_ai.prompt": "hello", "gen_ai.completion": "world"},
    )
    bw._trace_buffer["test-trace"] = [span]

    await bw._flush_trace("test-trace")

    # Cluster and assignment should be persisted
    async with async_session() as session:
        clusters = (await session.execute(select(BehaviorCluster))).scalars().all()
        assignments = (await session.execute(
            select(BehaviorAssignment).where(BehaviorAssignment.trace_id == "test-trace")
        )).scalars().all()

    assert len(clusters) == 1
    assert len(assignments) == 1
    assert assignments[0].trace_id == "test-trace"


async def test_flush_trace_clears_buffer(monkeypatch):
    from agentq.behaviors import worker as bw

    monkeypatch.setattr(bw, "_FLUSH_DELAY", 0.0)
    bw._trace_buffer.clear()
    bw._flush_tasks.clear()

    span = SpanRecord(
        trace_id="t99", span_id=str(uuid.uuid4()), name="x",
        span_kind="CLIENT", service_name="svc",
        start_time_unix_nano=0, end_time_unix_nano=1_000_000, duration_ms=1.0,
    )
    bw._trace_buffer["t99"] = [span]
    await bw._flush_trace("t99")

    assert "t99" not in bw._trace_buffer


async def test_flush_trace_empty_buffer_is_noop(monkeypatch):
    from agentq.behaviors import worker as bw
    monkeypatch.setattr(bw, "_FLUSH_DELAY", 0.0)
    bw._trace_buffer.clear()
    # Should not raise with an empty buffer
    await bw._flush_trace("no-such-trace")
