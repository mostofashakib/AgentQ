"""In-memory similar-call tracking keyed by argument fingerprint.

Used by the intercept circuit breaker (repeated tool calls with the *same
arguments*, not just the same tool name) and by cost-efficiency heuristics.
State is per-process and bounded; a restart only resets counters for runs
already in flight, which the per-run limits still cap.
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict


def fingerprint(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class SimilarCallTracker:
    def __init__(self, max_traces: int = 2000) -> None:
        self._max_traces = max_traces
        self._traces: OrderedDict[str, dict[str, int]] = OrderedDict()

    def record(self, trace_id: str, name: str, payload: object) -> int:
        counts = self._traces.get(trace_id)
        if counts is None:
            counts = {}
            self._traces[trace_id] = counts
            while len(self._traces) > self._max_traces:
                self._traces.popitem(last=False)
        self._traces.move_to_end(trace_id)
        key = f"{name}:{fingerprint(payload)}"
        counts[key] = counts.get(key, 0) + 1
        return counts[key]

    def reset(self, trace_id: str | None = None) -> None:
        if trace_id is None:
            self._traces.clear()
        else:
            self._traces.pop(trace_id, None)


similar_calls = SimilarCallTracker()
