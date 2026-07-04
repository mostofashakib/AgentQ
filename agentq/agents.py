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
) -> tuple[ConnectedAgent, str]:
    token = secrets.token_urlsafe(32)
    agent = (await session.execute(
        select(ConnectedAgent).where(ConnectedAgent.service_name == service_name)
    )).scalars().first()
    if agent is None:
        agent = ConnectedAgent(service_name=service_name, token_hash="")
        session.add(agent)
    agent.token_hash = hash_connection_token(token)
    agent.capture_traces = capture_traces
    agent.analyze_behavior = True
    agent.enabled = True
    await session.commit()
    await session.refresh(agent)
    return agent, token


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
