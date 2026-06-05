# tests/alerts/test_channels.py
import pytest
import httpx
from agentq.events import ViolationAlertEvent, BehaviorAlertEvent
from agentq.guardrails.models import ViolationRecord


def _violation_event() -> ViolationAlertEvent:
    return ViolationAlertEvent(violation=ViolationRecord(
        trace_id="t1", span_id="s1", rule_id="r1",
        threat_class="behavioral", severity="high",
        blocked=True, description="test violation",
    ))


def _behavior_event() -> BehaviorAlertEvent:
    return BehaviorAlertEvent(cluster_id="c1", trace_id="t1", similarity_score=0.95)


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
    assert posted["json"]["blocked"] is True


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
