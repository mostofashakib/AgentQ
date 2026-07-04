from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, model_validator
from typing import Literal
from urllib.parse import urlparse
from agentq.db.engine import get_session
from agentq.db.models import AppSettings
from agentq.guardrails.settings import get_app_settings, invalidate_cache
from agentq.api.security import require_admin, require_viewer

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    token_explosion_threshold: int | None = None
    excessive_tool_calls_threshold: int | None = None
    infinite_loop_repeat_threshold: int | None = None
    behavior_similarity_threshold: float | None = None
    default_alert_channel: dict | None = None
    llm_provider: Literal["anthropic", "openai", "openrouter", "huggingface", "local"] | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    @model_validator(mode="after")
    def validate_local_provider(self):
        if self.llm_provider == "local" and not self.llm_base_url:
            raise ValueError("Local provider requires llm_base_url")
        if self.llm_base_url:
            parsed = urlparse(self.llm_base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("llm_base_url must be an HTTP(S) URL")
            if parsed.username or parsed.password:
                raise ValueError("Credentials must not be embedded in llm_base_url")
        return self


async def _get_or_create_row(session: AsyncSession) -> AppSettings:
    # Delegate the get-or-create-with-correct-seeding logic to
    # agentq.guardrails.settings.get_app_settings(), which seeds
    # behavior_similarity_threshold from agentq.config.settings on first
    # creation. This guarantees the singleton row exists (and is seeded
    # correctly) before we re-select it in *this* session, since we need a
    # row bound to `session` to mutate and commit.
    await get_app_settings()
    row = (
        await session.execute(select(AppSettings).where(AppSettings.id == "singleton"))
    ).scalars().first()
    assert row is not None
    return row


@router.get("")
async def get_settings(_principal=Depends(require_viewer)):
    row = await get_app_settings()
    return _to_dict(row)


@router.put("")
async def update_settings(
    body: SettingsUpdate,
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_admin),
):
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
        "llm_provider": row.llm_provider,
        "llm_model": row.llm_model,
        "llm_base_url": row.llm_base_url,
        "llm_api_key_set": bool(row.llm_api_key),
    }
