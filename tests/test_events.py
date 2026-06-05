import asyncio
import pytest
from agentq.events import (
    span_queue, behavior_span_queue, trace_complete_queue, alert_event_queue,
    ViolationAlertEvent, BehaviorAlertEvent,
)
from agentq.guardrails.models import ViolationRecord


def test_queues_are_distinct_instances():
    assert span_queue is not behavior_span_queue
    assert span_queue is not trace_complete_queue
    assert span_queue is not alert_event_queue
    assert behavior_span_queue is not trace_complete_queue


def test_violation_alert_event_type_literal():
    v = ViolationRecord(
        trace_id="t1", span_id="s1", rule_id="r1",
        threat_class="behavioral", severity="high",
        blocked=False, description="test",
    )
    event = ViolationAlertEvent(violation=v)
    assert event.type == "violation"
    assert event.violation.trace_id == "t1"


def test_behavior_alert_event_type_literal():
    event = BehaviorAlertEvent(cluster_id="c1", trace_id="t1", similarity_score=0.91)
    assert event.type == "behavior"
    assert event.similarity_score == 0.91


def test_new_config_fields_have_defaults():
    from agentq.config import Settings
    s = Settings()
    assert s.smtp_host == ""
    assert s.smtp_port == 587
    assert s.smtp_from == ""
    assert s.smtp_to == ""
    assert s.slack_webhook_url == ""
    assert s.behavior_similarity_threshold == pytest.approx(0.82)
