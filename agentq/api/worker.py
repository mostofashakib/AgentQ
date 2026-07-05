# agentq/api/worker.py
from __future__ import annotations
import asyncio
import logging
import agentq.db.engine as _db_engine
from agentq.db.models import Violation, MonitoringEvent
from agentq.guardrails.registry import build_engine
from agentq.guardrails.models import ViolationRecord
from agentq.events import span_queue, alert_event_queue, ViolationAlertEvent
from agentq.api.routes.stream import broadcast
from agentq.monitoring.evaluators import evaluate_span
from agentq.monitoring.runs import record_evaluations
from agentq.monitoring.logging import log_event
from agentq.monitoring.redaction import redact_text

_verifier = build_engine()


async def _save_violations(span, violations: list[ViolationRecord] | None = None) -> None:
    # Keep the original test/integration helper signature compatible.
    if violations is None:
        violations = span
        span = None
    if not violations and span is None:
        return
    async with _db_engine.async_session() as session:
        for v in violations:
            session.add(Violation(
                id=v.id,
                trace_id=v.trace_id,
                span_id=v.span_id,
                rule_id=v.rule_id,
                threat_class=v.threat_class,
                severity=v.severity,
                description=v.description,
                evidence=redact_text(v.evidence) if v.evidence else None,
                chain_span_ids=v.chain_span_ids,
            ))
            # Deliberately not emit_monitoring_event: violations already alert via ViolationAlertEvent below.
            session.add(MonitoringEvent(
                trace_id=v.trace_id, span_id=v.span_id, event_type="security",
                category=v.rule_id, severity=v.severity, reason=v.description,
            ))
        if span is not None:
            evaluations = evaluate_span(span=span, violation_rule_ids={v.rule_id for v in violations})
            await record_evaluations(session, span.trace_id, evaluations)
            for result in evaluations:
                log_event("evaluation", trace_id=span.trace_id, span_id=span.span_id,
                          evaluator=result.evaluator, status=result.status, score=result.score, reason=result.reason)
        for violation in violations:
            log_event("guardrail", trace_id=violation.trace_id, span_id=violation.span_id,
                      rule_id=violation.rule_id, severity=violation.severity, decision="blocked_or_flagged")
        await session.commit()


async def guardrail_worker() -> None:
    while True:
        span = await span_queue.get()
        try:
            violations = await _verifier.run_all(span)
            await _save_violations(span, violations)
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
        except Exception:
            logging.getLogger(__name__).exception("guardrail_worker error processing span %s", span.span_id)
        finally:
            span_queue.task_done()
