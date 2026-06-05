import httpx
from agentq.config import settings
from agentq.guardrails.models import ViolationRecord


async def dispatch_violation(violation: ViolationRecord) -> None:
    if not settings.webhook_enabled or not settings.webhook_url:
        return
    payload = {
        "type": "violation",
        "rule_id": violation.rule_id,
        "threat_class": violation.threat_class,
        "severity": violation.severity,
        "description": violation.description,
        "trace_id": violation.trace_id,
        "span_id": violation.span_id,
        "evidence": violation.evidence,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(settings.webhook_url, json=payload)
        except httpx.HTTPError:
            pass  # webhook failures are non-fatal
