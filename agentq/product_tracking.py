from __future__ import annotations

import hashlib
import hmac
import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.models import ProductEvent
from agentq.monitoring.logging import log_event
from agentq.monitoring.redaction import redact
from agentq.monitoring.redaction import redact_text


ProductAction = Literal[
    "viewed", "started", "completed", "failed", "abandoned",
    "feedback_positive", "feedback_negative",
]


class ProductEventInput(BaseModel):
    feature: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    action: ProductAction
    user_id: str | None = Field(default=None, max_length=500)
    session_id: str | None = Field(default=None, max_length=200)
    trace_id: str | None = Field(default=None, max_length=200)
    metadata: dict = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def limit_metadata_size(cls, value: dict) -> dict:
        if len(json.dumps(value, default=str)) > 16_384:
            raise ValueError("metadata must not exceed 16 KiB")
        return value


class ProductEventTracker:
    """Records explicit product outcomes without retaining direct identifiers."""

    def __init__(self, session: AsyncSession, *, identity_salt: str, enabled: bool = True):
        self._session = session
        self._identity_salt = identity_salt
        self._enabled = enabled

    def _hash_identity(self, user_id: str | None) -> str | None:
        if not user_id or not self._identity_salt:
            return None
        return hmac.new(
            self._identity_salt.encode(), user_id.encode(), hashlib.sha256,
        ).hexdigest()

    async def track(self, data: ProductEventInput) -> ProductEvent | None:
        if not self._enabled:
            return None
        event = ProductEvent(
            feature=data.feature,
            action=data.action,
            user_id_hash=self._hash_identity(data.user_id),
            session_id=redact_text(data.session_id) if data.session_id else None,
            trace_id=redact_text(data.trace_id) if data.trace_id else None,
            metadata_json=redact(data.metadata),
        )
        self._session.add(event)
        await self._session.flush()
        log_event(
            "product_event",
            trace_id=event.trace_id,
            session_id=event.session_id,
            feature=event.feature,
            action=event.action,
        )
        return event
