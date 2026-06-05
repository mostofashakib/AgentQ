# agentq/api/alerts/channels/webhook.py
import httpx
from agentq.events import AlertEvent, ViolationAlertEvent


async def send(url: str, event: AlertEvent) -> None:
    if isinstance(event, ViolationAlertEvent):
        v = event.violation
        payload = {
            "type": "violation",
            "rule_id": v.rule_id,
            "threat_class": v.threat_class,
            "severity": v.severity,
            "description": v.description,
            "trace_id": v.trace_id,
            "span_id": v.span_id,
            "evidence": v.evidence,
        }
    else:
        payload = {
            "type": "behavior",
            "cluster_id": event.cluster_id,
            "trace_id": event.trace_id,
            "similarity_score": event.similarity_score,
        }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)
