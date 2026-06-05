from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class EvalScore(BaseModel):
    task_completion: Optional[float] = None   # 0.0-1.0
    tool_accuracy: Optional[float] = None     # 0.0-1.0
    efficiency: Optional[float] = None        # 0.0-1.0
    judge_score: Optional[float] = None       # 0.0-1.0
    judge_rationale: Optional[str] = None
    judge_flagged: bool = False


class EvalRequest(BaseModel):
    trace_id: str
    span_records: list  # list[SpanRecord] — typed as list to avoid circular import
    goal: Optional[str] = None
    expected_output: Optional[str] = None
    optimal_steps: Optional[int] = None
