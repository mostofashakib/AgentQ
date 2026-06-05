import pytest
from agentq.db.models import SpanRecord
from agentq.evals.models import EvalRequest
from agentq.evals.metrics import task_completion, tool_accuracy, efficiency
from agentq.evals.engine import score_trace


def make_span(name="chat", tool=None, status="STATUS_CODE_OK", **attrs) -> SpanRecord:
    return SpanRecord(
        trace_id="t1", span_id=name, name=name, span_kind="CLIENT",
        service_name="agent", start_time_unix_nano=0, end_time_unix_nano=1_000_000,
        duration_ms=1.0, gen_ai_tool_name=tool, status_code=status,
        attributes=attrs,
    )


def test_task_completion_exact_match():
    score = task_completion.score("hello world", "hello world")
    assert score == 1.0


def test_task_completion_no_expected():
    assert task_completion.score("anything", None) == 0.0


def test_tool_accuracy_all_ok():
    spans = [make_span(tool="search"), make_span(tool="lookup")]
    assert tool_accuracy.score(spans) == 1.0


def test_tool_accuracy_mixed():
    spans = [
        make_span(tool="search", status="STATUS_CODE_OK"),
        make_span(tool="lookup", status="STATUS_CODE_ERROR"),
    ]
    assert tool_accuracy.score(spans) == 0.5


def test_tool_accuracy_no_tools():
    spans = [make_span()]
    assert tool_accuracy.score(spans) == 1.0


def test_efficiency_optimal_equals_actual():
    spans = [make_span() for _ in range(3)]
    assert efficiency.score(spans, optimal_steps=3) == 1.0


def test_efficiency_too_many_steps():
    spans = [make_span() for _ in range(10)]
    assert efficiency.score(spans, optimal_steps=5) == 0.5


def test_efficiency_no_optimal():
    spans = [make_span() for _ in range(5)]
    assert efficiency.score(spans, optimal_steps=None) == 1.0


async def test_score_trace_no_judge():
    spans = [
        make_span("step1", **{"gen_ai.completion": "final answer"}),
        make_span("step2", tool="search"),
    ]
    request = EvalRequest(
        trace_id="t1",
        span_records=spans,
        expected_output="final answer",
        optimal_steps=2,
    )
    score = await score_trace(request)
    assert score.task_completion == 1.0
    assert score.tool_accuracy == 1.0
    assert score.efficiency == 1.0
    assert score.judge_score is None  # no goal = no judge


async def test_score_trace_partial():
    spans = [make_span("s1", tool="bad_tool", status="STATUS_CODE_ERROR")]
    request = EvalRequest(trace_id="t2", span_records=spans)
    score = await score_trace(request)
    assert score.tool_accuracy == 0.0
