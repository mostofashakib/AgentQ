from __future__ import annotations

import hashlib
import hmac
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.models import ConnectedAgent


def hash_connection_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_connection(
    session: AsyncSession,
    *,
    service_name: str,
    capture_traces: bool,
    integration_type: str = "otel",
) -> tuple[ConnectedAgent, str]:
    token = secrets.token_urlsafe(32)
    agent = (await session.execute(
        select(ConnectedAgent).where(ConnectedAgent.service_name == service_name)
    )).scalars().first()
    if agent is None:
        agent = ConnectedAgent(service_name=service_name, token_hash="")
        session.add(agent)
    agent.token_hash = hash_connection_token(token)
    agent.integration_type = integration_type
    agent.capture_traces = capture_traces
    agent.analyze_behavior = True
    agent.enabled = True
    agent.verified_at = None
    agent.last_seen_at = None
    await session.commit()
    await session.refresh(agent)
    return agent, token


def record_verified_telemetry(agent: ConnectedAgent) -> None:
    """Mark a registration verified only after its authenticated telemetry parsed."""
    from agentq.utils.time import utc_now

    now = utc_now()
    if agent.verified_at is None:
        agent.verified_at = now
    agent.last_seen_at = now


async def authorize_agent(
    session: AsyncSession, service_names: set[str], token: str | None,
) -> ConnectedAgent | None:
    if len(service_names) != 1 or not token:
        return None
    agent = (await session.execute(select(ConnectedAgent).where(
        ConnectedAgent.service_name == next(iter(service_names)),
        ConnectedAgent.enabled.is_(True),
    ))).scalars().first()
    if agent is None or not hmac.compare_digest(agent.token_hash, hash_connection_token(token)):
        return None
    return agent
