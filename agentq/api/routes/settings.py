from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from agentq.db.engine import get_session
from agentq.db.models import AppSettings
from agentq.guardrails.settings import invalidate_cache

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    token_explosion_threshold: int | None = None
    excessive_tool_calls_threshold: int | None = None
    infinite_loop_repeat_threshold: int | None = None
    behavior_similarity_threshold: float | None = None
    default_alert_channel: dict | None = None


async def _get_or_create_row(session: AsyncSession) -> AppSettings:
    row = (
        await session.execute(select(AppSettings).where(AppSettings.id == "singleton"))
    ).scalars().first()
    if row is None:
        row = AppSettings(id="singleton")
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


@router.get("")
async def get_settings(session: AsyncSession = Depends(get_session)):
    row = await _get_or_create_row(session)
    return _to_dict(row)


@router.put("")
async def update_settings(body: SettingsUpdate, session: AsyncSession = Depends(get_session)):
    row = await _get_or_create_row(session)
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    invalidate_cache()
    return _to_dict(row)


def _to_dict(row: AppSettings) -> dict:
    return {
        "token_explosion_threshold": row.token_explosion_threshold,
        "excessive_tool_calls_threshold": row.excessive_tool_calls_threshold,
        "infinite_loop_repeat_threshold": row.infinite_loop_repeat_threshold,
        "behavior_similarity_threshold": row.behavior_similarity_threshold,
        "default_alert_channel": row.default_alert_channel,
    }
