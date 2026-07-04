from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from agentq.config import settings

_active_database_url = settings.demo_database_url if settings.demo_mode else settings.database_url

engine = create_async_engine(
    _active_database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in _active_database_url else {},
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def create_tables() -> None:
    from agentq.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("app_settings")}
        )
        if "llm_base_url" not in columns:
            await conn.execute(text("ALTER TABLE app_settings ADD COLUMN llm_base_url VARCHAR"))
        await conn.execute(text("UPDATE connected_agents SET analyze_behavior = true"))
