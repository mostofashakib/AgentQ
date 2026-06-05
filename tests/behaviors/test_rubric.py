import pytest
import uuid
from agentq.db.models import BehaviorCluster, BehaviorAssignment, Span


async def _seed(session, cluster_id: str, trace_id: str):
    session.add(BehaviorCluster(
        id=cluster_id, name="Behavior-1",
        centroid=[0.1] * 384, trace_count=1,
    ))
    session.add(BehaviorAssignment(
        id=str(uuid.uuid4()), trace_id=trace_id,
        cluster_id=cluster_id, similarity_score=1.0,
    ))
    session.add(Span(
        trace_id=trace_id, span_id=str(uuid.uuid4()),
        name="chat", span_kind="CLIENT", service_name="agent",
        start_time_unix_nano=0, end_time_unix_nano=1_000_000,
        duration_ms=1.0, attributes={},
    ))
    await session.commit()


async def test_generate_rubric_updates_cluster_name_and_rubric(monkeypatch):
    from agentq.behaviors import rubric as rubric_mod
    from agentq.db.engine import async_session
    from sqlalchemy import select

    cluster_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    async with async_session() as session:
        await _seed(session, cluster_id, trace_id)

    # Mock the anthropic client
    class _FakeContent:
        text = '{"name": "Summarization Pattern", "criteria": ["Uses chat op", "Single turn"]}'

    class _FakeMsg:
        content = [_FakeContent()]

    class _FakeMessages:
        async def create(self, **kwargs):
            return _FakeMsg()

    class _FakeAnthropic:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _FakeAnthropic)

    async with async_session() as session:
        await rubric_mod.generate_rubric(session, cluster_id)

    async with async_session() as session:
        result = await session.execute(
            select(BehaviorCluster).where(BehaviorCluster.id == cluster_id)
        )
        cluster = result.scalars().first()

    assert cluster.name == "Summarization Pattern"
    assert "Uses chat op" in cluster.rubric


async def test_generate_rubric_missing_cluster_is_noop():
    from agentq.behaviors import rubric as rubric_mod
    from agentq.db.engine import async_session
    # Should not raise
    async with async_session() as session:
        await rubric_mod.generate_rubric(session, "nonexistent-id")
