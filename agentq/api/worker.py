# agentq/api/worker.py
from __future__ import annotations
import asyncio
from agentq.db.engine import async_session
from agentq.db.models import Violation
from agentq.guardrails.registry import build_engine
from agentq.guardrails.models import ViolationRecord
from agentq.events import span_queue, alert_event_queue, ViolationAlertEvent
from agentq.api.routes.stream import broadcast

_verifier = build_engine()


async def _save_violations(violations: list[ViolationRecord]) -> None:
    if not violations:
        return
    async with async_session() as session:
        for v in violations:
            session.add(Violation(
                id=v.id,
                trace_id=v.trace_id,
                span_id=v.span_id,
                rule_id=v.rule_id,
                threat_class=v.threat_class,
                severity=v.severity,
                blocked=v.blocked,
                description=v.description,
                evidence=v.evidence,
                chain_span_ids=v.chain_span_ids,
            ))
        await session.commit()


async def guardrail_worker() -> None:
    while True:
        span = await span_queue.get()
        violations = await _verifier.run_all(span)
        await _save_violations(violations)
        broadcast("span", {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "name": span.name,
            "span_kind": span.span_kind,
            "service_name": span.service_name,
            "duration_ms": span.duration_ms,
            "violation_count": len(violations),
        })
        for v in violations:
            broadcast("violation", {
                "rule_id": v.rule_id,
                "threat_class": v.threat_class,
                "severity": v.severity,
                "trace_id": v.trace_id,
            })
            await alert_event_queue.put(ViolationAlertEvent(violation=v))
