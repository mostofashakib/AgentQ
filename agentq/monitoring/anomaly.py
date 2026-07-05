from __future__ import annotations

from dataclasses import dataclass

from agentq.config import settings
from agentq.db.models import AgentRun


@dataclass(frozen=True)
class Anomaly:
    category: str
    severity: str
    reason: str


def detect_run_anomalies(run: AgentRun) -> list[Anomaly]:
    results: list[Anomaly] = []
    if (run.total_latency_ms or 0) > settings.unusual_latency_ms:
        results.append(Anomaly("latency_spike", "high", f"Run latency {run.total_latency_ms:.0f}ms exceeds threshold"))
    if (run.estimated_cost_usd or 0) > settings.unusual_cost_usd:
        results.append(Anomaly("cost_spike", "high", f"Run cost ${run.estimated_cost_usd:.4f} exceeds threshold"))
    if (run.output_tokens or 0) > settings.unusual_output_tokens:
        results.append(Anomaly("large_output", "medium", f"Output used {run.output_tokens} tokens"))
    if (run.tool_failure_count or 0) >= 3:
        results.append(Anomaly("repeated_tool_failures", "high", f"Run has {run.tool_failure_count} failed tool calls"))
    if (run.retry_count or 0) > settings.max_retries // 2:
        results.append(Anomaly("excessive_retries", "medium", f"Run has {run.retry_count} retries"))
    return results


def detect_format_change(model_spans) -> list[Anomaly]:
    """Producer-declared output formats (agentq.output_format) flipping mid-run."""
    formats = {span.attributes.get("agentq.output_format") for span in model_spans} - {None, ""}
    if len(formats) > 1:
        return [Anomaly("output_format_change", "medium",
                        f"Model output format changed mid-run: {sorted(formats)}")]
    return []
