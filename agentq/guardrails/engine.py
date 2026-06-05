from typing import Callable, Awaitable
from agentq.db.models import SpanRecord
from agentq.guardrails.models import ViolationRecord

RuleFn = Callable[[SpanRecord], Awaitable[list[ViolationRecord]]]


class VerifierEngine:
    def __init__(self) -> None:
        self._rules: list[tuple[str, RuleFn]] = []

    def register(self, rule_id: str, fn: RuleFn) -> None:
        self._rules.append((rule_id, fn))

    async def run_all(self, span: SpanRecord) -> list[ViolationRecord]:
        violations: list[ViolationRecord] = []
        for _rule_id, fn in self._rules:
            results = await fn(span)
            violations.extend(results)
        return violations
