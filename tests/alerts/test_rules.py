# tests/alerts/test_rules.py
import pytest
import uuid
from agentq.db.models import AlertRule
from agentq.events import ViolationAlertEvent, BehaviorAlertEvent
from agentq.guardrails.models import ViolationRecord


def _rule(conditions: dict) -> AlertRule:
    return AlertRule(
        id=str(uuid.uuid4()), name="test",
        conditions=conditions, channels=[],
        frequency_limit=0, cooldown_minutes=0, enabled=True,
    )


def _violation_event(severity="high", threat_class="behavioral", rule_id="r1") -> ViolationAlertEvent:
    v = ViolationRecord(
        trace_id="t1", span_id="s1", rule_id=rule_id,
        threat_class=threat_class, severity=severity,
        description="test",
    )
    return ViolationAlertEvent(violation=v)


def test_empty_conditions_matches_violation():
    from agentq.api.alerts.rules import matches
    assert matches(_rule({}), _violation_event()) is True


def test_empty_conditions_matches_behavior():
    from agentq.api.alerts.rules import matches
    event = BehaviorAlertEvent(cluster_id="c1", trace_id="t1", similarity_score=0.9)
    assert matches(_rule({}), event) is True


def test_severity_condition_matches():
    from agentq.api.alerts.rules import matches
    assert matches(_rule({"severity": "high"}), _violation_event(severity="high")) is True


def test_severity_condition_no_match():
    from agentq.api.alerts.rules import matches
    assert matches(_rule({"severity": "critical"}), _violation_event(severity="high")) is False


def test_threat_class_condition_matches():
    from agentq.api.alerts.rules import matches
    assert matches(_rule({"threat_class": "injection"}), _violation_event(threat_class="injection")) is True


def test_rule_id_condition_matches():
    from agentq.api.alerts.rules import matches
    assert matches(_rule({"rule_id": "behavioral.infinite_loop"}), _violation_event(rule_id="behavioral.infinite_loop")) is True


def test_multiple_conditions_all_must_match():
    from agentq.api.alerts.rules import matches
    rule = _rule({"severity": "high", "threat_class": "behavioral"})
    assert matches(rule, _violation_event(severity="high", threat_class="behavioral")) is True
    assert matches(rule, _violation_event(severity="low", threat_class="behavioral")) is False


def test_cluster_id_condition_matches_behavior_event():
    from agentq.api.alerts.rules import matches
    rule = _rule({"cluster_id": "cluster-abc"})
    event = BehaviorAlertEvent(cluster_id="cluster-abc", trace_id="t1", similarity_score=0.9)
    assert matches(rule, event) is True


def test_cluster_id_condition_no_match_behavior_event():
    from agentq.api.alerts.rules import matches
    rule = _rule({"cluster_id": "cluster-abc"})
    event = BehaviorAlertEvent(cluster_id="cluster-xyz", trace_id="t1", similarity_score=0.9)
    assert matches(rule, event) is False


def test_violation_specific_condition_does_not_match_behavior_event():
    from agentq.api.alerts.rules import matches
    rule = _rule({"severity": "high"})
    event = BehaviorAlertEvent(cluster_id="c1", trace_id="t1", similarity_score=0.9)
    assert matches(rule, event) is False
