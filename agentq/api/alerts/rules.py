# agentq/api/alerts/rules.py
from __future__ import annotations
from agentq.db.models import AlertRule
from agentq.events import AlertEvent, ViolationAlertEvent, BehaviorAlertEvent

_VIOLATION_FIELDS = {"severity", "threat_class", "rule_id"}
_BEHAVIOR_FIELDS = {"cluster_id"}


def matches(rule: AlertRule, event: AlertEvent) -> bool:
    conditions = rule.conditions or {}
    if not conditions:
        return True

    if isinstance(event, ViolationAlertEvent):
        # Behavior-only conditions never match violation events
        if conditions.keys() & _BEHAVIOR_FIELDS:
            return False
        v = event.violation
        if "severity" in conditions and conditions["severity"] != v.severity:
            return False
        if "threat_class" in conditions and conditions["threat_class"] != v.threat_class:
            return False
        if "rule_id" in conditions and conditions["rule_id"] != v.rule_id:
            return False
        return True

    if isinstance(event, BehaviorAlertEvent):
        # Violation-only conditions never match behavior events
        if conditions.keys() & _VIOLATION_FIELDS:
            return False
        if "cluster_id" in conditions and conditions["cluster_id"] != event.cluster_id:
            return False
        return True

    return False
