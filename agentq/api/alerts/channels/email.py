# agentq/api/alerts/channels/email.py
from __future__ import annotations
from agentq.events import AlertEvent, MonitoringAlertEvent, ViolationAlertEvent
from agentq.config import settings


def _build_body(event: AlertEvent, rule_name: str) -> tuple[str, str]:
    if isinstance(event, ViolationAlertEvent):
        v = event.violation
        subject = f"[AgentQ Alert] {rule_name} — {v.severity.upper()} {v.threat_class}"
        body = (
            f"Alert Rule: {rule_name}\n"
            f"Severity: {v.severity}\n"
            f"Threat Class: {v.threat_class}\n"
            f"Rule ID: {v.rule_id}\n"
            f"Trace ID: {v.trace_id}\n"
            f"Span ID: {v.span_id}\n"
            f"Description: {v.description}\n"
        )
    elif isinstance(event, MonitoringAlertEvent):
        subject = f"[AgentQ Alert] {rule_name} — {event.severity.upper()} {event.event_type}"
        body = (
            f"Alert Rule: {rule_name}\n"
            f"Event Type: {event.event_type}\n"
            f"Category: {event.category}\n"
            f"Severity: {event.severity}\n"
            f"Trace ID: {event.trace_id}\n"
            f"Reason: {event.reason}\n"
        )
    else:
        subject = f"[AgentQ Alert] {rule_name} — new behavior cluster match"
        body = (
            f"Alert Rule: {rule_name}\n"
            f"Cluster ID: {event.cluster_id}\n"
            f"Trace ID: {event.trace_id}\n"
            f"Similarity Score: {event.similarity_score:.3f}\n"
        )
    return subject, body


async def send(to_addr: str, event: AlertEvent, rule_name: str = "") -> None:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not settings.smtp_host:
        return  # SMTP not configured

    subject, body = _build_body(event, rule_name)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_addr
    msg.attach(MIMEText(body, "plain"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=True,
    )
