from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentq.db.models import SpanRecord

EvaluationStatus = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class Evaluation:
    evaluator: str
    status: EvaluationStatus
    score: float
    reason: str | None = None


def evaluate_span(span: SpanRecord, violation_rule_ids: set[str]) -> list[Evaluation]:
    """Deterministic signals that work without sending private content to another model."""
    attrs = span.attributes
    output = attrs.get("gen_ai.completion") or attrs.get("gen_ai.tool.result") or ""
    prompt = attrs.get("gen_ai.prompt") or ""
    grounded = bool(attrs.get("agentq.grounded", attrs.get("agentq.source_count", 0)))
    required = attrs.get("agentq.required_items", [])
    completed = attrs.get("agentq.completed_items", [])

    faithfulness = Evaluation("faithfulness", "pass" if grounded else "warn", 1.0 if grounded else 0.5,
                              None if grounded else "No grounding signal or approved source metadata was supplied")
    relevant_signal = attrs.get("agentq.relevant")
    relevancy = Evaluation("relevancy", "pass" if relevant_signal is not False else "fail",
                           1.0 if relevant_signal is not False else 0.0,
                           None if relevant_signal is not False else "Producer marked the response as irrelevant")
    missing = [item for item in required if item not in completed] if isinstance(required, list) and isinstance(completed, list) else []
    completeness = Evaluation("completeness", "fail" if missing else "pass", 0.0 if missing else 1.0,
                              f"Missing required items: {missing[:10]}" if missing else None)
    hallucination_rules = {"behavioral.hallucinated_tool", "exfiltration.url_in_output"}
    hallucination = Evaluation("hallucination_risk", "fail" if violation_rule_ids & hallucination_rules else "pass",
                               0.0 if violation_rule_ids & hallucination_rules else 1.0,
                               "Unsupported tool or output claim detected" if violation_rule_ids & hallucination_rules else None)
    policy_fail = bool(violation_rule_ids)
    policy = Evaluation("policy_adherence", "fail" if policy_fail else "pass", 0.0 if policy_fail else 1.0,
                        f"Guardrail violations: {sorted(violation_rule_ids)[:5]}" if policy_fail else None)
    if not prompt and not output:
        relevancy = Evaluation("relevancy", "warn", 0.5, "No safe content or producer relevancy signal available")
    return [faithfulness, relevancy, completeness, hallucination, policy]
