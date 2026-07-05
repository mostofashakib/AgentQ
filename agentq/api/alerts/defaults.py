"""Zero-config default alert rules, seeded once into an empty alert_rules table.

Users get useful safety alerts out of the box; every rule is visible and
editable in the Alerts dashboard, and deleting them all does not re-seed.
Rules without channels dispatch to AppSettings.default_alert_channel when set.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.models import AlertRule

DEFAULT_RULES: list[dict] = [
    {"name": "Critical security violations", "conditions": {"severity": "critical"},
     "frequency_limit": 12, "cooldown_minutes": 5},
    {"name": "Circuit breaker fired", "conditions": {"event_type": "circuit_breaker"},
     "frequency_limit": 12, "cooldown_minutes": 10},
    {"name": "High-severity anomalies", "conditions": {"event_type": "anomaly", "severity": "high"},
     "frequency_limit": 6, "cooldown_minutes": 15},
    {"name": "Human approval rejected", "conditions": {"event_type": "approval", "category": "rejected"},
     "frequency_limit": 12, "cooldown_minutes": 5},
]


async def seed_default_alert_rules(session: AsyncSession) -> int:
    existing = (await session.execute(select(func.count(AlertRule.id)))).scalar_one()
    if existing:
        return 0
    for spec in DEFAULT_RULES:
        session.add(AlertRule(channels=[], enabled=True, **spec))
    return len(DEFAULT_RULES)
