# agentq/api/alerts/channels/webhook.py
import httpx
from agentq.events import AlertEvent, MonitoringAlertEvent, ViolationAlertEvent


def _payload(event: AlertEvent) -> dict:
    if isinstance(event, ViolationAlertEvent):
        v = event.violation
        return {"type": "violation", "rule_id": v.rule_id, "threat_class": v.threat_class,
                "severity": v.severity, "description": v.description,
                "trace_id": v.trace_id, "span_id": v.span_id, "evidence": v.evidence}
    if isinstance(event, MonitoringAlertEvent):
        return {"type": "monitoring", "event_type": event.event_type, "category": event.category,
                "severity": event.severity, "reason": event.reason,
                "trace_id": event.trace_id, "agent_run_id": event.agent_run_id, "span_id": event.span_id}
    return {"type": "behavior", "cluster_id": event.cluster_id,
            "trace_id": event.trace_id, "similarity_score": event.similarity_score}


async def send(url: str, event: AlertEvent) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=_payload(event))
