from typing import Any
from agentq.db.models import SpanRecord
from agentq.ingest.mcp_adapter import is_mcp_span, normalize_mcp_attrs

_SPAN_KIND_MAP = {
    0: "UNSPECIFIED", 1: "INTERNAL", 2: "SERVER",
    3: "CLIENT", 4: "PRODUCER", 5: "CONSUMER",
}

_PROTO_STATUS_CODE_MAP = {
    0: "STATUS_CODE_UNSET", 1: "STATUS_CODE_OK", 2: "STATUS_CODE_ERROR",
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


def _build_span_record(
    *,
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    name: str,
    kind: int,
    service_name: str,
    start_ns: int,
    end_ns: int,
    status_code: str,
    attrs: dict,
    resource_attrs: dict,
) -> SpanRecord:
    if is_mcp_span(attrs):
        attrs = normalize_mcp_attrs(attrs)
    finish_reasons = attrs.get("gen_ai.response.finish_reasons", [])
    if isinstance(finish_reasons, str):
        finish_reasons = [finish_reasons]
    return SpanRecord(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id or None,
        name=name,
        span_kind=_SPAN_KIND_MAP.get(kind, "UNSPECIFIED"),
        service_name=service_name,
        start_time_unix_nano=start_ns,
        end_time_unix_nano=end_ns,
        duration_ms=(end_ns - start_ns) / 1_000_000,
        status_code=status_code,
        gen_ai_system=attrs.get("gen_ai.system"),
        gen_ai_operation=attrs.get("gen_ai.operation.name"),
        gen_ai_input_tokens=attrs.get("gen_ai.usage.input_tokens"),
        gen_ai_output_tokens=attrs.get("gen_ai.usage.output_tokens"),
        gen_ai_tool_name=attrs.get("gen_ai.tool.name"),
        gen_ai_finish_reasons=finish_reasons or [],
        attributes={**resource_attrs, **attrs},
    )


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
                start_ns = int(raw.get("startTimeUnixNano", 0))
                end_ns = int(raw.get("endTimeUnixNano", 0))
                records.append(_build_span_record(
                    trace_id=raw.get("traceId", ""),
                    span_id=raw.get("spanId", ""),
                    parent_span_id=raw.get("parentSpanId") or None,
                    name=raw.get("name", ""),
                    kind=raw.get("kind", 0),
                    service_name=service_name,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    status_code=raw.get("status", {}).get("code", "STATUS_CODE_UNSET"),
                    attrs=attrs,
                    resource_attrs=resource_attrs,
                ))
    return records


def parse_otlp_protobuf(body: bytes) -> list[SpanRecord]:
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )

    request = ExportTraceServiceRequest()
    request.ParseFromString(body)

    def proto_value(value) -> Any:
        kind = value.WhichOneof("value")
        if kind == "string_value":
            return value.string_value
        if kind == "int_value":
            return value.int_value
        if kind == "double_value":
            return value.double_value
        if kind == "bool_value":
            return value.bool_value
        if kind == "array_value":
            return [proto_value(v) for v in value.array_value.values]
        return None

    def proto_attrs(raw) -> dict:
        return {kv.key: proto_value(kv.value) for kv in raw}

    records: list[SpanRecord] = []
    for resource_span in request.resource_spans:
        resource_attrs = proto_attrs(resource_span.resource.attributes)
        service_name = str(resource_attrs.get("service.name", "unknown"))
        for scope_span in resource_span.scope_spans:
            for span in scope_span.spans:
                attrs = proto_attrs(span.attributes)
                records.append(_build_span_record(
                    trace_id=span.trace_id.hex(),
                    span_id=span.span_id.hex(),
                    parent_span_id=span.parent_span_id.hex() or None,
                    name=span.name,
                    kind=span.kind,
                    service_name=service_name,
                    start_ns=span.start_time_unix_nano,
                    end_ns=span.end_time_unix_nano,
                    status_code=_PROTO_STATUS_CODE_MAP.get(span.status.code, "STATUS_CODE_UNSET"),
                    attrs=attrs,
                    resource_attrs=resource_attrs,
                ))
    return records
