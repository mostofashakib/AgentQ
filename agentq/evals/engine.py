from __future__ import annotations
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import async_session
from agentq.db.models import EvalResult, SpanRecord
from agentq.evals.models import EvalScore, EvalRequest
from agentq.evals import metrics


async def score_trace(request: EvalRequest) -> EvalScore:
    spans = request.span_records
    task_comp = metrics.task_completion.score(
        actual_output=_get_final_output(spans),
        expected_output=request.expected_output,
    )
    tool_acc = metrics.tool_accuracy.score(spans)
    eff = metrics.efficiency.score(spans, request.optimal_steps)
    score = EvalScore(
        task_completion=task_comp,
        tool_accuracy=tool_acc,
        efficiency=eff,
    )
    if request.goal:
        from agentq.evals.judges.factory import get_judge
        judge = get_judge()
        transcript = _build_transcript(spans)
        final_output = _get_final_output(spans)
        try:
            judge_result = await judge.judge(request.goal, transcript, final_output)
            score.judge_score = judge_result.judge_score
            score.judge_rationale = judge_result.judge_rationale
            score.judge_flagged = judge_result.judge_flagged
        except Exception:
            pass  # judge failures are non-fatal; metrics still recorded
    return score


async def persist_score(trace_id: str, score: EvalScore) -> None:
    async with async_session() as session:
        existing = await _get_existing(session, trace_id)
        if existing:
            existing.task_completion = score.task_completion
            existing.tool_accuracy = score.tool_accuracy
            existing.efficiency = score.efficiency
            existing.judge_score = score.judge_score
            existing.judge_rationale = score.judge_rationale
            existing.judge_flagged = score.judge_flagged
        else:
            session.add(EvalResult(
                trace_id=trace_id,
                task_completion=score.task_completion,
                tool_accuracy=score.tool_accuracy,
                efficiency=score.efficiency,
                judge_score=score.judge_score,
                judge_rationale=score.judge_rationale,
                judge_flagged=score.judge_flagged,
            ))
        await session.commit()


def _get_final_output(spans: list) -> str:
    for s in reversed(spans):
        completion = s.attributes.get("gen_ai.completion", "")
        if completion:
            return str(completion)
    return ""


def _build_transcript(spans: list) -> str:
    lines = []
    for s in spans:
        prompt = s.attributes.get("gen_ai.prompt", "")
        completion = s.attributes.get("gen_ai.completion", "")
        if prompt:
            lines.append(f"[{s.name}] USER: {prompt[:400]}")
        if completion:
            lines.append(f"[{s.name}] ASSISTANT: {completion[:400]}")
        if s.gen_ai_tool_name:
            lines.append(f"[{s.name}] TOOL: {s.gen_ai_tool_name}")
    return "\n".join(lines)


async def _get_existing(session: AsyncSession, trace_id: str) -> Optional[EvalResult]:
    from sqlalchemy import select
    result = await session.execute(select(EvalResult).where(EvalResult.trace_id == trace_id))
    return result.scalars().first()


class TieredEvalEngine:
    """Async worker that pulls SpanRecords from a queue and scores them by trace."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[SpanRecord] = asyncio.Queue()
        self._trace_buffer: dict[str, list[SpanRecord]] = {}
        self._flush_delay: float = 5.0  # seconds to wait after last span before scoring

    def enqueue(self, span: SpanRecord) -> None:
        self._queue.put_nowait(span)

    async def run(self) -> None:
        while True:
            span = await self._queue.get()
            trace_id = span.trace_id
            if trace_id not in self._trace_buffer:
                self._trace_buffer[trace_id] = []
            self._trace_buffer[trace_id].append(span)
            asyncio.create_task(self._flush_after_delay(trace_id))

    async def _flush_after_delay(self, trace_id: str) -> None:
        await asyncio.sleep(self._flush_delay)
        spans = self._trace_buffer.pop(trace_id, [])
        if not spans:
            return
        request = EvalRequest(trace_id=trace_id, span_records=spans)
        score = await score_trace(request)
        await persist_score(trace_id, score)
