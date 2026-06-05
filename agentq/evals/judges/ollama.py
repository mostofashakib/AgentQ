from __future__ import annotations
import json
import httpx
from agentq.config import settings
from agentq.evals.judges.base import AbstractJudge
from agentq.evals.models import EvalScore


_PROMPT_TPL = (
    "You are an AI agent evaluator. Score the agent performance.\n"
    "Goal: {goal}\nTranscript:\n{transcript}\nFinal output:\n{output}\n\n"
    'Respond with ONLY valid JSON: {{"score": 0.0-1.0, "rationale": "one sentence", "flagged": true/false}}'
)


class OllamaJudge(AbstractJudge):
    async def judge(self, goal: str, transcript: str, actual_output: str) -> EvalScore:
        prompt = _PROMPT_TPL.format(
            goal=goal, transcript=transcript[:3000], output=actual_output[:1000]
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.judge_model, "prompt": prompt, "stream": False},
            )
        raw = resp.json().get("response", "")
        try:
            data = json.loads(raw.strip())
            return EvalScore(
                judge_score=float(data.get("score", 0.5)),
                judge_rationale=str(data.get("rationale", "")),
                judge_flagged=bool(data.get("flagged", False)),
            )
        except (json.JSONDecodeError, KeyError):
            return EvalScore(judge_score=0.5, judge_rationale=raw[:200], judge_flagged=False)
