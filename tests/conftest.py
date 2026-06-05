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

    yield

    await engine.dispose()
