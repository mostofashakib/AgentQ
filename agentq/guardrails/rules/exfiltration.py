import re
from agentq.db.models import SpanRecord
from agentq.guardrails.models import ViolationRecord
from agentq.guardrails.utils.pattern_match import find_exfiltration, find_pii

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|secret[_-]?key|password|passwd|token|bearer|authorization)\s*[=:]\s*\S+",
    re.IGNORECASE,
)
_HTTP_TOOLS = {"http_request", "make_request", "fetch_url", "requests_get", "requests_post"}


async def url_in_output(span: SpanRecord) -> list[ViolationRecord]:
    completion = span.attributes.get("gen_ai.completion", "")
    if not isinstance(completion, str):
        return []
    evidence = find_exfiltration(completion)
    if not evidence or not evidence.startswith("http"):
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="exfiltration.url_in_output",
        threat_class="exfiltration", severity="medium", blocked=False,
        description="Model output contains a URL that may indicate data exfiltration",
        evidence=evidence[:200],
    )]


async def base64_in_output(span: SpanRecord) -> list[ViolationRecord]:
    completion = span.attributes.get("gen_ai.completion", "")
    if not isinstance(completion, str):
        return []
    if re.search(r"data:[^;]+;base64,|base64\.b64encode", completion, re.IGNORECASE):
        return [ViolationRecord(
            trace_id=span.trace_id, span_id=span.span_id,
            rule_id="exfiltration.base64_in_output",
            threat_class="exfiltration", severity="high", blocked=True,
            description="Model output contains base64-encoded data",
            evidence=completion[:200],
        )]
    return []


async def sensitive_key_in_output(span: SpanRecord) -> list[ViolationRecord]:
    completion = span.attributes.get("gen_ai.completion", "")
    if not isinstance(completion, str):
        return []
    m = _SENSITIVE_KEY_PATTERN.search(completion)
    if not m:
        return []
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="exfiltration.sensitive_key_in_output",
        threat_class="exfiltration", severity="critical", blocked=True,
        description="Model output contains what appears to be a credential or API key",
        evidence=m.group(0)[:100],
    )]


async def pii_in_output(span: SpanRecord) -> list[ViolationRecord]:
    completion = span.attributes.get("gen_ai.completion", "")
    if not isinstance(completion, str):
        return []
    result = find_pii(completion)
    if not result:
        return []
    matched, label = result
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="exfiltration.pii_in_output",
        threat_class="exfiltration", severity="critical", blocked=True,
        description=f"Model output contains PII ({label})",
        evidence=matched[:100],
    )]


async def outbound_http_tool(span: SpanRecord) -> list[ViolationRecord]:
    tool = (span.gen_ai_tool_name or "").lower()
    if tool not in _HTTP_TOOLS:
        return []
    url = span.attributes.get("gen_ai.tool.call.arguments", {})
    if isinstance(url, dict):
        url_str = str(url.get("url", ""))
    else:
        url_str = str(url)
    return [ViolationRecord(
        trace_id=span.trace_id, span_id=span.span_id,
        rule_id="exfiltration.outbound_http",
        threat_class="exfiltration", severity="high", blocked=False,
        description=f"Agent made outbound HTTP call via tool '{tool}'",
        evidence=url_str[:200],
    )]
