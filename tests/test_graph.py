import pytest
from agentq.api.routes.graph import _build_graph


class _MockSpan:
    def __init__(self, span_id, parent_span_id, service_name, operation, name, duration_ms=10.0):
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.service_name = service_name
        self.gen_ai_operation = operation
        self.name = name
        self.duration_ms = duration_ms


def test_build_graph_single_service_no_edges():
    spans = [
        _MockSpan("s1", None, "agent", "chat", "chat"),
        _MockSpan("s2", "s1", "agent", "chat", "chat"),
    ]
    result = _build_graph(spans)
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["service_name"] == "agent"
    assert result["nodes"][0]["span_count"] == 2
    assert result["edges"] == []


def test_build_graph_two_services_one_edge():
    spans = [
        _MockSpan("s1", None, "orchestrator", "chat", "chat", duration_ms=20.0),
        _MockSpan("s2", "s1", "tool-service", "search", "search", duration_ms=10.0),
    ]
    result = _build_graph(spans)
    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["source"] == "orchestrator/chat"
    assert edge["target"] == "tool-service/search"
    assert edge["call_count"] == 1


def test_build_graph_empty():
    assert _build_graph([]) == {"nodes": [], "edges": []}


def test_build_graph_avg_duration():
    spans = [
        _MockSpan("s1", None, "agent", "chat", "chat", duration_ms=10.0),
        _MockSpan("s2", None, "agent", "chat", "chat", duration_ms=20.0),
    ]
    result = _build_graph(spans)
    assert result["nodes"][0]["avg_duration_ms"] == pytest.approx(15.0)
