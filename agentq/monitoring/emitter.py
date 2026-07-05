"""Single funnel for safety-relevant monitoring events: persist + log + alert."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.models import MonitoringEvent
from agentq.events import alert_event_queue, MonitoringAlertEvent
from agentq.monitoring.logging import log_event

# Trace id used for aggregate (cross-run) events that have no single owning trace.
AGGREGATE_TRACE_ID = "aggregate"

_LEVELS = {"low": logging.INFO, "medium": logging.INFO, "high": logging.WARNING, "critical": logging.ERROR}


async def emit_monitoring_event(
    session: AsyncSession,
    *,
    trace_id: str,
    event_type: str,
    category: str,
    severity: str,
    reason: str,
    agent_run_id: str | None = None,
    span_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    notify: bool = True,
) -> MonitoringEvent:
    event = MonitoringEvent(
        trace_id=trace_id, agent_run_id=agent_run_id, span_id=span_id,
        event_type=event_type, category=category, severity=severity,
        reason=reason, metadata_json=metadata or {},
    )
    session.add(event)
    log_event(event_type, trace_id=trace_id, agent_run_id=agent_run_id, span_id=span_id,
              level=_LEVELS.get(severity, logging.INFO), category=category,
              severity=severity, reason=reason)
    if notify:
        await alert_event_queue.put(MonitoringAlertEvent(
            trace_id=trace_id, agent_run_id=agent_run_id, span_id=span_id,
            event_type=event_type, category=category, severity=severity, reason=reason,
        ))
    return event
