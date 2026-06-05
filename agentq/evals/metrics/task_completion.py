from __future__ import annotations
from typing import Optional


def score(actual_output: str, expected_output: Optional[str]) -> float:
    if not expected_output or not actual_output:
        return 0.0
    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(["rouge1"], use_stemmer=True)
    result = scorer.score(expected_output, actual_output)
    return round(float(result["rouge1"].fmeasure), 4)
