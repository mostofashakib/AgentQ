from __future__ import annotations
from abc import ABC, abstractmethod
from agentq.evals.models import EvalScore


class AbstractJudge(ABC):
    @abstractmethod
    async def judge(
        self,
        goal: str,
        transcript: str,
        actual_output: str,
    ) -> EvalScore:
        """Score a completed agent trace. Returns EvalScore with judge_score 0-1."""
        ...
