from __future__ import annotations
import json
from agentq.config import settings
from agentq.evals.judges.base import AbstractJudge
from agentq.evals.models import EvalScore


_SYSTEM = (
    "You are an AI agent evaluator. Score the agent's performance.\n"
    "Respond with ONLY valid JSON: "
    '{"score": 0.0-1.0, "rationale": "one sentence", "flagged": true/false}'
)


class OpenAIJudge(AbstractJudge):
    async def judge(self, goal: str, transcript: str, actual_output: str) -> EvalScore:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = (
            f"Goal: {goal}\n\nTranscript:\n{transcript[:3000]}\n\nFinal output:\n{actual_output[:1000]}"
        )
        resp = await client.chat.completions.create(
            model=settings.judge_model,
            max_tokens=256,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content or ""
        try:
            data = json.loads(raw.strip())
            return EvalScore(
                judge_score=float(data.get("score", 0.5)),
                judge_rationale=str(data.get("rationale", "")),
                judge_flagged=bool(data.get("flagged", False)),
            )
        except (json.JSONDecodeError, KeyError):
            return EvalScore(judge_score=0.5, judge_rationale=raw[:200], judge_flagged=False)
