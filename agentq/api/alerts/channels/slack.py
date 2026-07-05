# agentq/api/alerts/channels/slack.py
import httpx
from agentq.events import AlertEvent, MonitoringAlertEvent, ViolationAlertEvent

_SEVERITY_EMOJI = {"low": "🔵", "medium": "🟡", "high": "🟠", "critical": "🔴"}


def _build_blocks(event: AlertEvent, rule_name: str) -> list:
    if isinstance(event, ViolationAlertEvent):
        v = event.violation
        emoji = _SEVERITY_EMOJI.get(v.severity, "⚪")
        text = (
            f"{emoji} *{rule_name}*\n"
            f"*Severity:* {v.severity}  |  *Class:* {v.threat_class}\n"
            f"*Rule:* `{v.rule_id}`\n"
            f"*Trace:* `{v.trace_id}`\n"
            f"{v.description}"
        )
    elif isinstance(event, MonitoringAlertEvent):
        emoji = _SEVERITY_EMOJI.get(event.severity, "⚪")
        text = (
            f"{emoji} *{rule_name}*\n"
            f"*Event:* {event.event_type}  |  *Category:* `{event.category}`\n"
            f"*Severity:* {event.severity}\n"
            f"*Trace:* `{event.trace_id}`\n"
            f"{event.reason}"
        )
    else:
        text = (
            f"🔍 *{rule_name}*\n"
            f"*Cluster:* `{event.cluster_id}`\n"
            f"*Trace:* `{event.trace_id}`\n"
            f"*Similarity:* {event.similarity_score:.2f}"
        )
    return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]


async def send(webhook_url: str, event: AlertEvent, rule_name: str = "") -> None:
    blocks = _build_blocks(event, rule_name)
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(webhook_url, json={"blocks": blocks})
