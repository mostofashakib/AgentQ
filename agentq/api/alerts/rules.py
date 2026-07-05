# agentq/api/alerts/rules.py
from __future__ import annotations
from agentq.db.models import AlertRule
from agentq.events import AlertEvent, ViolationAlertEvent, BehaviorAlertEvent, MonitoringAlertEvent

_VIOLATION_FIELDS = {"threat_class", "rule_id"}
_BEHAVIOR_FIELDS = {"cluster_id"}
_MONITORING_FIELDS = {"event_type", "category"}
# "severity" is shared: it applies to both violations and monitoring events.


def matches(rule: AlertRule, event: AlertEvent) -> bool:
    conditions = rule.conditions or {}
    if not conditions:
        return True
    keys = conditions.keys()

    if isinstance(event, ViolationAlertEvent):
        if keys & (_BEHAVIOR_FIELDS | _MONITORING_FIELDS):
            return False
        v = event.violation
        checks = {"severity": v.severity, "threat_class": v.threat_class, "rule_id": v.rule_id}
        return all(key in checks and conditions[key] == checks[key] for key in keys)

    if isinstance(event, BehaviorAlertEvent):
        if keys & (_VIOLATION_FIELDS | _MONITORING_FIELDS | {"severity"}):
            return False
        return conditions.get("cluster_id", event.cluster_id) == event.cluster_id

    if isinstance(event, MonitoringAlertEvent):
        if keys & (_VIOLATION_FIELDS | _BEHAVIOR_FIELDS):
            return False
        checks = {"severity": event.severity, "event_type": event.event_type, "category": event.category}
        return all(key in checks and conditions[key] == checks[key] for key in keys)

    return False
