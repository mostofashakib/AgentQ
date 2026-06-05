from __future__ import annotations
from typing import Optional


def score(span_records: list, optimal_steps: Optional[int]) -> float:
    if not optimal_steps or optimal_steps <= 0:
        return 1.0
    actual = len(span_records)
    if actual == 0:
        return 1.0
    return round(min(1.0, optimal_steps / actual), 4)
