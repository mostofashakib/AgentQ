from __future__ import annotations
from datetime import datetime
from sqlalchemy import select
import agentq.db.engine as _db_engine
from agentq.db.models import AppSettings
from agentq.config import settings as env_settings

_cache: AppSettings | None = None
_cached_at: datetime | None = None
_REFRESH_INTERVAL = 60


async def get_app_settings() -> AppSettings:
    global _cache, _cached_at
    now = datetime.utcnow()
    if _cache is not None and _cached_at and (now - _cached_at).total_seconds() < _REFRESH_INTERVAL:
        return _cache

    async with _db_engine.async_session() as session:
        row = (
            await session.execute(select(AppSettings).where(AppSettings.id == "singleton"))
        ).scalars().first()
        if row is None:
            row = AppSettings(
                id="singleton",
                behavior_similarity_threshold=env_settings.behavior_similarity_threshold,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)

    _cache = row
    _cached_at = now
    return row


def invalidate_cache() -> None:
    global _cached_at
    _cached_at = None
