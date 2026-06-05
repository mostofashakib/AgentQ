import pytest
import numpy as np
from agentq.db.models import SpanRecord


def _make_span(trace_id="t1", span_id="s1", operation="chat", tool=None,
               prompt="hello", completion="world", start=0):
    return SpanRecord(
        trace_id=trace_id, span_id=span_id, name=operation,
        span_kind="CLIENT", service_name="agent",
        start_time_unix_nano=start, end_time_unix_nano=start + 1_000_000,
        duration_ms=1.0, gen_ai_operation=operation, gen_ai_tool_name=tool,
        attributes={"gen_ai.prompt": prompt, "gen_ai.completion": completion},
    )


def test_compute_composite_returns_unit_vector():
    from agentq.behaviors.embedder import compute_composite
    spans = [_make_span()]
    vec = compute_composite(spans)
    assert len(vec) == 384
    norm = float(np.linalg.norm(vec))
    assert abs(norm - 1.0) < 1e-5


def test_compute_composite_empty_spans_returns_zero_vector():
    from agentq.behaviors.embedder import compute_composite
    vec = compute_composite([])
    assert len(vec) == 384
    assert all(v == 0.0 for v in vec)


def test_compute_composite_different_content_different_vectors():
    from agentq.behaviors.embedder import compute_composite
    span_a = _make_span(prompt="summarize this document", completion="here is a summary")
    span_b = _make_span(prompt="translate to french", completion="voici la traduction")
    va = np.array(compute_composite([span_a]))
    vb = np.array(compute_composite([span_b]))
    similarity = float(np.dot(va, vb))
    assert similarity < 0.999


def test_compute_composite_structural_uses_tool_name():
    from agentq.behaviors.embedder import compute_composite
    # Two spans: same prompt/completion, different tool sequences
    span_search = _make_span(tool="web_search", prompt="same", completion="same")
    span_calc = _make_span(tool="calculator", prompt="same", completion="same")
    vs = np.array(compute_composite([span_search]))
    vc = np.array(compute_composite([span_calc]))
    # Different tools → vectors should differ
    assert float(np.dot(vs, vc)) < 0.9999
