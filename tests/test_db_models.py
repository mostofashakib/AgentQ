import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from agentq.db.models import Base, Span, Violation, EvalResult, SpanRecord


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_span_insert(session):
    span = Span(
        trace_id="abc123",
        span_id="span001",
        name="chat claude",
        span_kind="CLIENT",
        service_name="my-agent",
        start_time_unix_nano=1_000_000_000,
        end_time_unix_nano=1_100_000_000,
        duration_ms=100.0,
    )
    session.add(span)
    await session.commit()
    result = await session.get(Span, span.id)
    assert result.trace_id == "abc123"
    assert result.duration_ms == 100.0


async def test_violation_insert(session):
    v = Violation(
        trace_id="abc123",
        span_id="span001",
        rule_id="injection.user_content",
        threat_class="injection",
        severity="high",
        blocked=True,
        description="Injection detected",
        evidence="ignore all previous",
    )
    session.add(v)
    await session.commit()
    result = await session.get(Violation, v.id)
    assert result.threat_class == "injection"
    assert result.blocked is True


async def test_span_record_pydantic():
    r = SpanRecord(
        trace_id="t1",
        span_id="s1",
        name="tool call",
        span_kind="CLIENT",
        service_name="agent",
        start_time_unix_nano=0,
        end_time_unix_nano=1_000_000,
        duration_ms=1.0,
    )
    assert r.gen_ai_system is None
    assert r.gen_ai_finish_reasons == []
