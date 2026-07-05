# tests/alerts/test_channels.py
import pytest
import httpx
from agentq.events import ViolationAlertEvent, BehaviorAlertEvent, MonitoringAlertEvent
from agentq.guardrails.models import ViolationRecord


def _violation_event() -> ViolationAlertEvent:
    return ViolationAlertEvent(violation=ViolationRecord(
        trace_id="t1", span_id="s1", rule_id="r1",
        threat_class="behavioral", severity="high",
        description="test violation",
    ))


def _behavior_event() -> BehaviorAlertEvent:
    return BehaviorAlertEvent(cluster_id="c1", trace_id="t1", similarity_score=0.95)


def _monitoring_event() -> MonitoringAlertEvent:
    return MonitoringAlertEvent(
        trace_id="t1", agent_run_id="run1", span_id="s1",
        event_type="circuit_breaker", category="run_limit",
        severity="high", reason="maximum tool calls reached",
    )


async def test_webhook_sends_violation_payload(monkeypatch):
    from agentq.api.alerts.channels import webhook
    posted = {}

    async def mock_post(self, url, json=None, **kwargs):
        posted["url"] = url
        posted["json"] = json
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    await webhook.send("http://test.local/hook", _violation_event())

    assert posted["json"]["type"] == "violation"
    assert posted["json"]["severity"] == "high"
    assert posted["json"]["trace_id"] == "t1"


async def test_webhook_sends_behavior_payload(monkeypatch):
    from agentq.api.alerts.channels import webhook
    posted = {}

    async def mock_post(self, url, json=None, **kwargs):
        posted["json"] = json
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    await webhook.send("http://test.local/hook", _behavior_event())

    assert posted["json"]["type"] == "behavior"
    assert posted["json"]["cluster_id"] == "c1"
    assert posted["json"]["similarity_score"] == pytest.approx(0.95)


async def test_webhook_sends_monitoring_payload(monkeypatch):
    from agentq.api.alerts.channels import webhook
    posted = {}

    async def mock_post(self, url, json=None, **kwargs):
        posted["json"] = json
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    await webhook.send("http://test.local/hook", _monitoring_event())

    assert posted["json"]["type"] == "monitoring"
    assert posted["json"]["event_type"] == "circuit_breaker"
    assert posted["json"]["category"] == "run_limit"
    assert posted["json"]["severity"] == "high"
    assert posted["json"]["reason"] == "maximum tool calls reached"
    assert posted["json"]["trace_id"] == "t1"


async def test_slack_sends_block_kit_message(monkeypatch):
    from agentq.api.alerts.channels import slack
    posted = {}

    async def mock_post(self, url, json=None, **kwargs):
        posted["url"] = url
        posted["json"] = json
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    await slack.send("http://hooks.slack.com/test", _violation_event(), rule_name="My Rule")

    assert posted["url"] == "http://hooks.slack.com/test"
    assert "blocks" in posted["json"]
    blocks_text = str(posted["json"]["blocks"])
    assert "My Rule" in blocks_text
    assert "high" in blocks_text


async def test_slack_sends_monitoring_message(monkeypatch):
    from agentq.api.alerts.channels import slack
    posted = {}

    async def mock_post(self, url, json=None, **kwargs):
        posted["url"] = url
        posted["json"] = json
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    await slack.send("http://hooks.slack.com/test", _monitoring_event(), rule_name="Monitoring Rule")

    assert "blocks" in posted["json"]
    blocks_text = str(posted["json"]["blocks"])
    assert "Monitoring Rule" in blocks_text
    assert "circuit_breaker" in blocks_text
    assert "run_limit" in blocks_text
    assert "high" in blocks_text
    assert "t1" in blocks_text
    assert "maximum tool calls reached" in blocks_text


async def test_email_build_body_violation():
    from agentq.api.alerts.channels.email import _build_body
    subject, body = _build_body(_violation_event(), rule_name="Critical Rule")
    assert "Critical Rule" in subject
    assert "high" in body
    assert "t1" in body


async def test_email_build_body_behavior():
    from agentq.api.alerts.channels.email import _build_body
    subject, body = _build_body(_behavior_event(), rule_name="Cluster Alert")
    assert "Cluster Alert" in subject
    assert "c1" in body


async def test_email_build_body_monitoring():
    from agentq.api.alerts.channels.email import _build_body
    subject, body = _build_body(_monitoring_event(), rule_name="Monitoring Rule")
    assert "Monitoring Rule" in subject
    assert "HIGH" in subject
    assert "circuit_breaker" in subject
    assert "run_limit" in body
    assert "t1" in body
    assert "maximum tool calls reached" in body
