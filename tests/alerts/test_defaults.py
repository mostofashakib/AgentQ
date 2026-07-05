from sqlalchemy import select

import agentq.db.engine as db_engine
from agentq.db.models import AlertRule
from agentq.api.alerts.defaults import seed_default_alert_rules


async def test_seeds_rules_into_empty_table():
    async with db_engine.async_session() as session:
        inserted = await seed_default_alert_rules(session)
        await session.commit()
    assert inserted == 4
    async with db_engine.async_session() as session:
        rules = (await session.execute(select(AlertRule))).scalars().all()
    names = {rule.name for rule in rules}
    assert "Critical security violations" in names
    assert all(rule.cooldown_minutes > 0 for rule in rules)  # noise-safe defaults


async def test_does_not_reseed_when_any_rule_exists():
    async with db_engine.async_session() as session:
        session.add(AlertRule(name="mine", conditions={}, channels=[]))
        await session.commit()
    async with db_engine.async_session() as session:
        inserted = await seed_default_alert_rules(session)
        await session.commit()
    assert inserted == 0
    async with db_engine.async_session() as session:
        rules = (await session.execute(select(AlertRule))).scalars().all()
    assert len(rules) == 1
