# tests/alerts/test_worker.py
import pytest
import asyncio
import uuid
from agentq.db.models import AlertRule, AlertHistory
import agentq.db.engine as _db_engine
import agentq.events as _events_module
from agentq.events import ViolationAlertEvent, BehaviorAlertEvent, MonitoringAlertEvent
from agentq.guardrails.models import ViolationRecord
from sqlalchemy import select


async def _insert_rule(session, conditions: dict, channels: list, rule_id: str | None = None):
    rid = rule_id or str(uuid.uuid4())
    session.add(AlertRule(
        id=rid, name="Test Rule",
        conditions=conditions, channels=channels,
        frequency_limit=10, cooldown_minutes=0, enabled=True,
    ))
    await session.commit()
    return rid


async def test_alert_worker_dispatches_matching_rule(monkeypatch):
    from agentq.api.alerts import worker as aw
    from agentq.api.alerts.cooldown import cooldown_tracker

    cooldown_tracker._state.clear()
    aw._rules_refreshed_at = None

    # Fresh queue bound to the current event loop
    fresh_queue: asyncio.Queue = asyncio.Queue()
    monkeypatch.setattr(_events_module, "alert_event_queue", fresh_queue)
    monkeypatch.setattr(aw, "alert_event_queue", fresh_queue)

    async with _db_engine.async_session() as session:
        rid = await _insert_rule(
            session,
            conditions={"severity": "high"},
            channels=[{"type": "webhook", "url": "http://test.local/hook"}],
        )

    dispatched = []

    async def fake_dispatch(channel_cfg, event, rule_name):
        dispatched.append(channel_cfg["type"])
        return channel_cfg["type"]

    monkeypatch.setattr(aw, "_dispatch_channel", fake_dispatch)

    v = ViolationRecord(
        trace_id="t1", span_id="s1", rule_id="r1",
        threat_class="behavioral", severity="high",
        description="test",
    )
    await fresh_queue.put(ViolationAlertEvent(violation=v))

    task = asyncio.create_task(aw.alert_worker())
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert "webhook" in dispatched

    async with _db_engine.async_session() as session:
        history = (await session.execute(select(AlertHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].rule_id == rid
    assert history[0].channel == "webhook"


async def test_alert_worker_skips_non_matching_rule(monkeypatch):
    from agentq.api.alerts import worker as aw
    from agentq.api.alerts.cooldown import cooldown_tracker

    cooldown_tracker._state.clear()
    aw._rules_refreshed_at = None

    # Fresh queue bound to the current event loop
    fresh_queue: asyncio.Queue = asyncio.Queue()
    monkeypatch.setattr(_events_module, "alert_event_queue", fresh_queue)
    monkeypatch.setattr(aw, "alert_event_queue", fresh_queue)

    async with _db_engine.async_session() as session:
        await _insert_rule(
            session,
            conditions={"severity": "critical"},  # won't match "high"
            channels=[{"type": "webhook", "url": "http://test.local"}],
        )

    dispatched = []

    async def fake_dispatch(channel_cfg, event, rule_name):
        dispatched.append(channel_cfg["type"])
        return channel_cfg["type"]

    monkeypatch.setattr(aw, "_dispatch_channel", fake_dispatch)

    v = ViolationRecord(
        trace_id="t2", span_id="s2", rule_id="r2",
        threat_class="injection", severity="high",
        description="test",
    )
    await fresh_queue.put(ViolationAlertEvent(violation=v))

    task = asyncio.create_task(aw.alert_worker())
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert dispatched == []


async def test_alert_worker_respects_cooldown(monkeypatch):
    from agentq.api.alerts import worker as aw
    from agentq.api.alerts.cooldown import cooldown_tracker

    cooldown_tracker._state.clear()
    aw._rules_refreshed_at = None

    # Fresh queue bound to the current event loop
    fresh_queue: asyncio.Queue = asyncio.Queue()
    monkeypatch.setattr(_events_module, "alert_event_queue", fresh_queue)
    monkeypatch.setattr(aw, "alert_event_queue", fresh_queue)

    async with _db_engine.async_session() as session:
        rid = await _insert_rule(
            session,
            conditions={},
            channels=[{"type": "webhook", "url": "http://test.local"}],
        )
        from sqlalchemy import select as sa_select
        rule = (await session.execute(sa_select(AlertRule).where(AlertRule.id == rid))).scalars().first()
        rule.cooldown_minutes = 60
        rule.frequency_limit = 1
        await session.commit()

    dispatched = []

    async def fake_dispatch(channel_cfg, event, rule_name):
        dispatched.append(1)
        return channel_cfg["type"]

    monkeypatch.setattr(aw, "_dispatch_channel", fake_dispatch)

    v = ViolationRecord(trace_id="t3", span_id="s3", rule_id="r3", threat_class="behavioral", severity="low", description="x")

    # First event — should fire
    await fresh_queue.put(ViolationAlertEvent(violation=v))
    task = asyncio.create_task(aw.alert_worker())
    await asyncio.sleep(0.05)
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass

    # Second event — should be blocked by cooldown
    aw._rules_refreshed_at = None
    await fresh_queue.put(ViolationAlertEvent(violation=v))
    task = asyncio.create_task(aw.alert_worker())
    await asyncio.sleep(0.05)
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass

    assert len(dispatched) == 1  # only fired once


async def test_alert_worker_falls_back_to_default_channel_when_rule_channels_empty(monkeypatch):
    from agentq.api.alerts import worker as aw
    from agentq.api.alerts.cooldown import cooldown_tracker
    from agentq.guardrails import settings as guardrail_settings
    from agentq.db.models import AppSettings

    cooldown_tracker._state.clear()
    aw._rules_refreshed_at = None
    guardrail_settings.invalidate_cache()

    # Fresh queue bound to the current event loop
    fresh_queue: asyncio.Queue = asyncio.Queue()
    monkeypatch.setattr(_events_module, "alert_event_queue", fresh_queue)
    monkeypatch.setattr(aw, "alert_event_queue", fresh_queue)

    async with _db_engine.async_session() as session:
        rid = await _insert_rule(session, conditions={}, channels=[])
        session.add(AppSettings(
            id="singleton",
            default_alert_channel={"type": "webhook", "url": "http://default.local/hook"},
        ))
        await session.commit()

    dispatched = []

    async def fake_dispatch(channel_cfg, event, rule_name):
        dispatched.append(channel_cfg)
        return channel_cfg["type"]

    monkeypatch.setattr(aw, "_dispatch_channel", fake_dispatch)

    v = ViolationRecord(
        trace_id="t4", span_id="s4", rule_id="r4",
        threat_class="behavioral", severity="high",
        description="test",
    )
    await fresh_queue.put(ViolationAlertEvent(violation=v))

    task = asyncio.create_task(aw.alert_worker())
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(dispatched) == 1
    assert dispatched[0] == {"type": "webhook", "url": "http://default.local/hook"}

    async with _db_engine.async_session() as session:
        history = (await session.execute(select(AlertHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].rule_id == rid


async def test_monitoring_alert_event_flows_to_alert_history(monkeypatch):
    from agentq.api.alerts import worker as aw
    from agentq.api.alerts.cooldown import cooldown_tracker

    cooldown_tracker._state.clear()
    aw._rules_refreshed_at = None

    # Fresh queue bound to the current event loop
    fresh_queue: asyncio.Queue = asyncio.Queue()
    monkeypatch.setattr(_events_module, "alert_event_queue", fresh_queue)
    monkeypatch.setattr(aw, "alert_event_queue", fresh_queue)

    async with _db_engine.async_session() as session:
        rid = await _insert_rule(
            session,
            conditions={"event_type": "circuit_breaker"},
            channels=[{"type": "webhook", "url": "http://test.local/hook"}],
        )

    dispatched = []

    async def fake_dispatch(channel_cfg, event, rule_name):
        dispatched.append(channel_cfg["type"])
        return channel_cfg["type"]

    monkeypatch.setattr(aw, "_dispatch_channel", fake_dispatch)

    event = MonitoringAlertEvent(
        trace_id="t5", span_id="s5", event_type="circuit_breaker",
        category="run_limit", severity="high", reason="maximum tool calls reached",
    )
    await fresh_queue.put(event)

    task = asyncio.create_task(aw.alert_worker())
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert "webhook" in dispatched

    async with _db_engine.async_session() as session:
        history = (await session.execute(select(AlertHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].rule_id == rid
    assert history[0].trace_id == "t5"
    assert history[0].span_id == "s5"
    assert history[0].channel == "webhook"
