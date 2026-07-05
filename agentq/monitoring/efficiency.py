"""Cost-efficiency heuristics over a run's model spans. Pure functions, no I/O."""
from __future__ import annotations

from collections import Counter

from agentq.config import settings
from agentq.db.models import Span
from agentq.monitoring.anomaly import Anomaly
from agentq.monitoring.cost import is_premium_model


def _model_name(span: Span) -> str | None:
    return span.attributes.get("gen_ai.request.model") or span.attributes.get("gen_ai.response.model") or span.gen_ai_system


def detect_cost_inefficiencies(model_spans: list[Span]) -> list[Anomaly]:
    results: list[Anomaly] = []
    if not model_spans:
        return results

    fingerprints = Counter(
        (_model_name(span), span.attributes.get("agentq.prompt_fingerprint"))
        for span in model_spans if span.attributes.get("agentq.prompt_fingerprint")
    )
    repeats = {key: count for key, count in fingerprints.items() if count >= settings.max_similar_model_calls}
    if repeats:
        (model, _), count = max(repeats.items(), key=lambda item: item[1])
        results.append(Anomaly("repeated_similar_prompts", "medium",
                               f"{count} calls to {model} with an identical prompt; consider caching the response"))

    def _tokens(span: Span) -> int:
        return (span.gen_ai_input_tokens or 0) + (span.gen_ai_output_tokens or 0)

    if (all(_tokens(span) <= settings.cheap_task_token_threshold for span in model_spans)
            and any(is_premium_model(_model_name(span)) for span in model_spans)):
        model = next(_model_name(s) for s in model_spans if is_premium_model(_model_name(s)))
        results.append(Anomaly("expensive_model_for_small_task", "low",
                               f"All model calls used <= {settings.cheap_task_token_threshold} tokens but ran on "
                               f"premium model {model}; a cheaper model would likely satisfy this task"))
    return results
