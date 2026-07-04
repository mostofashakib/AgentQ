from __future__ import annotations

import hmac
from dataclasses import dataclass
from enum import IntEnum

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from agentq.config import settings


class AccessLevel(IntEnum):
    INGEST = 1
    VIEWER = 2
    ADMIN = 3


@dataclass(frozen=True)
class Principal:
    identity: str
    access_level: AccessLevel


_api_key_header = APIKeyHeader(name="X-AgentQ-API-Key", auto_error=False)


def _matches(provided: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(provided.encode(), expected.encode())


def _principal_for_key(api_key: str | None) -> Principal | None:
    if not api_key:
        return None
    if _matches(api_key, settings.admin_api_key):
        return Principal("api-key:admin", AccessLevel.ADMIN)
    if _matches(api_key, settings.viewer_api_key):
        return Principal("api-key:viewer", AccessLevel.VIEWER)
    if _matches(api_key, settings.ingest_api_key):
        return Principal("api-key:ingest", AccessLevel.INGEST)
    return None


def require_access(required: AccessLevel):
    async def dependency(api_key: str | None = Depends(_api_key_header)) -> Principal:
        if not settings.auth_required:
            return Principal("local-development", AccessLevel.ADMIN)

        principal = _principal_for_key(api_key)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid API key is required",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        if principal.access_level < required:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return principal

    return dependency


require_ingest = require_access(AccessLevel.INGEST)
require_viewer = require_access(AccessLevel.VIEWER)
require_admin = require_access(AccessLevel.ADMIN)
