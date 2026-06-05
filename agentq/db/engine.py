from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from agentq.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def create_tables() -> None:
    from agentq.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
