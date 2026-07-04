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


async def _configure_llm_key(monkeypatch, api_key: str = "sk-ant-fake-key") -> None:
    from agentq.guardrails import settings as guardrail_settings
    from agentq.config import settings as env_settings

    guardrail_settings.invalidate_cache()
    monkeypatch.setattr(env_settings, "anthropic_api_key", api_key)


async def test_generate_rubric_updates_cluster_name_and_rubric(monkeypatch):
    from agentq.behaviors import rubric as rubric_mod
    from agentq.db.engine import async_session
    from sqlalchemy import select

    await _configure_llm_key(monkeypatch)

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


async def test_generate_rubric_skips_with_message_when_no_api_key(monkeypatch):
    from agentq.behaviors import rubric as rubric_mod
    from agentq.guardrails import settings as guardrail_settings
    from agentq.config import settings as env_settings
    from agentq.db.engine import async_session
    from sqlalchemy import select

    guardrail_settings.invalidate_cache()
    monkeypatch.setattr(env_settings, "anthropic_api_key", "")

    cluster_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    async with async_session() as session:
        await _seed(session, cluster_id, trace_id)

    async with async_session() as session:
        await rubric_mod.generate_rubric(session, cluster_id)

    async with async_session() as session:
        result = await session.execute(
            select(BehaviorCluster).where(BehaviorCluster.id == cluster_id)
        )
        cluster = result.scalars().first()

    assert cluster.description == "Rubric generation skipped — no LLM API key configured. Add one in Settings."


async def test_generate_rubric_sets_failure_message_on_exception(monkeypatch):
    from agentq.behaviors import rubric as rubric_mod
    from agentq.db.engine import async_session
    from sqlalchemy import select

    await _configure_llm_key(monkeypatch)

    cluster_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    async with async_session() as session:
        await _seed(session, cluster_id, trace_id)

    class _FailingAnthropic:
        def __init__(self, api_key):
            pass

        @property
        def messages(self):
            raise RuntimeError("boom")

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _FailingAnthropic)

    async with async_session() as session:
        await rubric_mod.generate_rubric(session, cluster_id)

    async with async_session() as session:
        result = await session.execute(
            select(BehaviorCluster).where(BehaviorCluster.id == cluster_id)
        )
        cluster = result.scalars().first()

    assert cluster.description == "Rubric generation failed — check server logs."
