"""
Shared test configuration.

For the API tests we patch the database engine to use an in-memory SQLite
database so that:
  1. Tests are isolated from any on-disk agentq.db file.
  2. The engine/session used by app routes matches the one whose tables we
     created, even though the FastAPI lifespan also calls create_tables().
"""
import pytest
from contextlib import AsyncExitStack
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import agentq.db.engine as db_engine_module
from agentq.db.models import Base
from agentq.guardrails import settings as guardrail_settings
from agentq.api import rate_limit


# Track whether the app's lifespan has been initialized in this session
_app_lifespan_initialized = False
_app_lifespan_stack = None


@pytest.fixture(autouse=True, scope="session")
async def _initialize_app_lifespan():
    """Initialize the app's lifespan once per test session."""
    global _app_lifespan_initialized, _app_lifespan_stack

    if not _app_lifespan_initialized:
        from agentq.api.app import app as main_app

        _app_lifespan_stack = AsyncExitStack()
        await _app_lifespan_stack.__aenter__()
        await _app_lifespan_stack.enter_async_context(main_app.router.lifespan_context(main_app))
        _app_lifespan_initialized = True

    yield


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
