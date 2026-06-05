from typing import Any
from agentq.db.models import SpanRecord
from agentq.ingest.mcp_adapter import is_mcp_span, normalize_mcp_attrs

_SPAN_KIND_MAP = {
    0: "UNSPECIFIED", 1: "INTERNAL", 2: "SERVER",
    3: "CLIENT", 4: "PRODUCER", 5: "CONSUMER",
}


def _extract_value(value: dict) -> Any:
    if "stringValue" in value:
        return value["stringValue"]
    if "intValue" in value:
        return int(value["intValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "boolValue" in value:
        return value["boolValue"]
    if "arrayValue" in value:
        return [_extract_value(v) for v in value["arrayValue"].get("values", [])]
    return None


def _attrs_dict(raw: list[dict]) -> dict:
    return {
        a["key"]: _extract_value(a["value"])
        for a in raw
        if "key" in a and "value" in a
    }


def parse_otlp_json(payload: dict) -> list[SpanRecord]:
    records: list[SpanRecord] = []
    for resource_span in payload.get("resourceSpans", []):
        resource_attrs = _attrs_dict(
            resource_span.get("resource", {}).get("attributes", [])
        )
        service_name = str(resource_attrs.get("service.name", "unknown"))
        for scope_span in resource_span.get("scopeSpans", []):
            for raw in scope_span.get("spans", []):
                attrs = _attrs_dict(raw.get("attributes", []))
                if is_mcp_span(attrs):
                    attrs = normalize_mcp_attrs(attrs)
                start_ns = int(raw.get("startTimeUnixNano", 0))
                end_ns = int(raw.get("endTimeUnixNano", 0))
                finish_reasons = attrs.get("gen_ai.response.finish_reasons", [])
                if isinstance(finish_reasons, str):
                    finish_reasons = [finish_reasons]
                records.append(SpanRecord(
                    trace_id=raw.get("traceId", ""),
                    span_id=raw.get("spanId", ""),
                    parent_span_id=raw.get("parentSpanId") or None,
                    name=raw.get("name", ""),
                    span_kind=_SPAN_KIND_MAP.get(raw.get("kind", 0), "UNSPECIFIED"),
                    service_name=service_name,
                    start_time_unix_nano=start_ns,
                    end_time_unix_nano=end_ns,
                    duration_ms=(end_ns - start_ns) / 1_000_000,
                    status_code=raw.get("status", {}).get("code", "STATUS_CODE_UNSET"),
                    gen_ai_system=attrs.get("gen_ai.system"),
                    gen_ai_operation=attrs.get("gen_ai.operation.name"),
                    gen_ai_input_tokens=attrs.get("gen_ai.usage.input_tokens"),
                    gen_ai_output_tokens=attrs.get("gen_ai.usage.output_tokens"),
                    gen_ai_tool_name=attrs.get("gen_ai.tool.name"),
                    gen_ai_finish_reasons=finish_reasons or [],
                    attributes={**resource_attrs, **attrs},
                ))
    return records
