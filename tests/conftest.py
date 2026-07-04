"""
Shared test configuration.

For the API tests we patch the database engine to use an in-memory SQLite
database so that:
  1. Tests are isolated from any on-disk agentq.db file.
  2. The engine/session used by app routes matches the one whose tables we
     created, even though the FastAPI lifespan also calls create_tables().
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import agentq.db.engine as db_engine_module
from agentq.db.models import Base
from agentq.guardrails import settings as guardrail_settings
from agentq.api import rate_limit

TEST_AGENT_TOKEN = "test-agent-connection-token"


@pytest.fixture(autouse=True, scope="function")
async def _use_memory_db(monkeypatch):
    """Replace the module-level engine and session-maker with in-memory equivalents."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Create all tables upfront
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _get_session():
        async with session_maker() as session:
            yield session

    monkeypatch.setattr(db_engine_module, "engine", engine)
    monkeypatch.setattr(db_engine_module, "async_session", session_maker)
    monkeypatch.setattr(db_engine_module, "get_session", _get_session)

    # agentq.guardrails.settings caches the AppSettings row at module scope
    # across a refresh window, independent of which DB engine is active. Since
    # each test gets a brand new in-memory engine above, a cache entry left
    # over from a previous test would point at an already-disposed engine and
    # mask the fresh DB's actual (empty) state. Reset it so every test starts
    # with a cold cache against its own fresh DB.
    guardrail_settings.invalidate_cache()
    rate_limit.reset()

    yield

    await engine.dispose()


@pytest.fixture
def connected_agent_factory():
    async def create(*service_names: str, token: str = TEST_AGENT_TOKEN):
        from agentq.agents import hash_connection_token
        from agentq.db.models import ConnectedAgent

        async with db_engine_module.async_session() as session:
            session.add_all([
                ConnectedAgent(
                    service_name=name,
                    token_hash=hash_connection_token(token),
                    capture_traces=True,
                    analyze_behavior=True,
                )
                for name in service_names
            ])
            await session.commit()
        return token

    return create
