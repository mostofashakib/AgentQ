# agentq/api/alerts/worker.py
from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from agentq.db.models import AlertRule, AlertHistory
import agentq.db.engine as _db_engine
from agentq.events import alert_event_queue, AlertEvent, ViolationAlertEvent
from agentq.api.alerts.cooldown import cooldown_tracker
from agentq.api.alerts.rules import matches
from agentq.guardrails.settings import get_app_settings
from agentq.utils.time import utc_now

logger = logging.getLogger(__name__)

_rules_cache: list[AlertRule] = []
_rules_refreshed_at: datetime | None = None
_REFRESH_INTERVAL = 60


async def _load_rules() -> list[AlertRule]:
    global _rules_cache, _rules_refreshed_at
    now = utc_now()
    if _rules_refreshed_at and (now - _rules_refreshed_at).total_seconds() < _REFRESH_INTERVAL:
        return _rules_cache
    async with _db_engine.async_session() as session:
        result = await session.execute(
            select(AlertRule).where(AlertRule.enabled == True)
        )
        _rules_cache = list(result.scalars().all())
    _rules_refreshed_at = now
    return _rules_cache


async def _dispatch_channel(channel_cfg: dict, event: AlertEvent, rule_name: str) -> str:
    ctype = channel_cfg.get("type", "")
    try:
        if ctype == "webhook":
            from agentq.api.alerts.channels import webhook
            await webhook.send(channel_cfg["url"], event)
        elif ctype == "slack":
            from agentq.api.alerts.channels import slack
            await slack.send(channel_cfg["url"], event, rule_name)
        elif ctype == "email":
            from agentq.api.alerts.channels import email as email_channel
            await email_channel.send(channel_cfg.get("to", ""), event, rule_name)
        return ctype
    except Exception as exc:
        logger.warning("Alert channel %s failed: %s", ctype, exc)
        return f"failed:{ctype}"


async def alert_worker() -> None:
    while True:
        event = await alert_event_queue.get()
        try:
            rules = await _load_rules()

            if isinstance(event, ViolationAlertEvent):
                trace_id, span_id = event.violation.trace_id, event.violation.span_id
            else:
                trace_id, span_id = event.trace_id, getattr(event, "span_id", None)

            for rule in rules:
                if not matches(rule, event):
                    continue
                if not cooldown_tracker.can_fire(rule.id, rule.frequency_limit, rule.cooldown_minutes):
                    continue

                cooldown_tracker.record_fire(rule.id)

                channels = list(rule.channels or [])
                if not channels:
                    app_settings = await get_app_settings()
                    if app_settings.default_alert_channel:
                        channels = [app_settings.default_alert_channel]
                for channel_cfg in channels:
                    channel_label = await _dispatch_channel(channel_cfg, event, rule.name)
                    async with _db_engine.async_session() as session:
                        session.add(AlertHistory(
                            rule_id=rule.id,
                            trace_id=trace_id,
                            span_id=span_id,
                            channel=channel_label,
                            fired_at=utc_now(),
                        ))
                        await session.commit()
        except Exception:
            logger.exception("alert_worker error processing event")
        finally:
            alert_event_queue.task_done()
