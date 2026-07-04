from datetime import datetime
from agentq.api.routes.agents import _build_agents


class _MockSpan:
    def __init__(self, trace_id, service_name, created_at):
        self.trace_id = trace_id
        self.service_name = service_name
        self.created_at = created_at


class _MockViolation:
    def __init__(self, trace_id):
        self.trace_id = trace_id


def test_build_agents_empty():
    assert _build_agents([], []) == []


def test_build_agents_single_service():
    spans = [
        _MockSpan("t1", "research-agent", datetime(2026, 1, 1, 10, 0, 0)),
        _MockSpan("t1", "research-agent", datetime(2026, 1, 1, 10, 0, 5)),
        _MockSpan("t2", "research-agent", datetime(2026, 1, 1, 10, 5, 0)),
    ]
    result = _build_agents(spans, [])
    assert len(result) == 1
    a = result[0]
    assert a["service_name"] == "research-agent"
    assert a["span_count"] == 3
    assert a["first_seen"] == datetime(2026, 1, 1, 10, 0, 0).isoformat()
    assert a["last_seen"] == datetime(2026, 1, 1, 10, 5, 0).isoformat()
    assert a["violation_count"] == 0


def test_build_agents_two_services_with_violations():
    spans = [
        _MockSpan("t1", "agent-a", datetime(2026, 1, 1, 10, 0, 0)),
        _MockSpan("t2", "agent-b", datetime(2026, 1, 1, 11, 0, 0)),
    ]
    violations = [_MockViolation("t1"), _MockViolation("t1"), _MockViolation("t2")]
    result = {a["service_name"]: a for a in _build_agents(spans, violations)}
    assert result["agent-a"]["violation_count"] == 2
    assert result["agent-b"]["violation_count"] == 1


def test_build_agents_violation_for_unseen_trace_ignored():
    spans = [_MockSpan("t1", "agent-a", datetime(2026, 1, 1, 10, 0, 0))]
    violations = [_MockViolation("unknown-trace")]
    result = _build_agents(spans, violations)
    assert result[0]["violation_count"] == 0
