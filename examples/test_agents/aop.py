from __future__ import annotations

import json
import time
import uuid
from enum import Enum
from typing import Any


class Integration(str, Enum):
    OPENCLAW = "openclaw"
    OTEL = "otel"
    OTEL_PROTOBUF = "otel-protobuf"
    MCP = "mcp"
    CURL = "curl"


def _json_value(value: Any) -> dict:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": value}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, list):
        return {"arrayValue": {"values": [_json_value(item) for item in value]}}
    if not isinstance(value, str):
        value = json.dumps(value, separators=(",", ":"))
    return {"stringValue": value}


def _integration_attributes(integration: Integration, name: str, attributes: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(attributes)
    if integration is Integration.MCP:
        enriched["mcp.method.name"] = name
        enriched["mcp.server.name"] = "test-agent-tools"
        if tool_name := enriched.get("gen_ai.tool.name"):
            enriched["mcp.tool.name"] = tool_name
    elif integration is Integration.OPENCLAW:
        enriched["openclaw.integration"] = "diagnostics-otel"
    enriched["agentq.integration.type"] = integration.value
    return enriched


def build_json_export(
    *, integration: Integration, service_name: str, name: str, attributes: dict[str, Any],
) -> dict:
    now = time.time_ns()
    span_attributes = _integration_attributes(integration, name, attributes)
    return {
        "resourceSpans": [{
            "resource": {"attributes": [
                {"key": "service.name", "value": {"stringValue": service_name}},
            ]},
            "scopeSpans": [{"scope": {"name": "agentq.test-agent"}, "spans": [{
                "traceId": uuid.uuid4().hex,
                "spanId": uuid.uuid4().hex[:16],
                "name": name,
                "kind": 3,
                "startTimeUnixNano": str(now),
                "endTimeUnixNano": str(time.time_ns()),
                "attributes": [
                    {"key": key, "value": _json_value(value)}
                    for key, value in span_attributes.items()
                ],
                "status": {"code": "STATUS_CODE_OK"},
            }]}],
        }],
    }


def build_protobuf_export(
    *, integration: Integration, service_name: str, name: str, attributes: dict[str, Any],
) -> bytes:
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span, Status

    def any_value(value: Any) -> AnyValue:
        if isinstance(value, bool):
            return AnyValue(bool_value=value)
        if isinstance(value, int):
            return AnyValue(int_value=value)
        if isinstance(value, float):
            return AnyValue(double_value=value)
        if not isinstance(value, str):
            value = json.dumps(value, separators=(",", ":"))
        return AnyValue(string_value=value)

    now = time.time_ns()
    enriched = _integration_attributes(integration, name, attributes)
    span = Span(
        trace_id=uuid.uuid4().bytes,
        span_id=uuid.uuid4().bytes[:8],
        name=name,
        kind=Span.SPAN_KIND_CLIENT,
        start_time_unix_nano=now,
        end_time_unix_nano=time.time_ns(),
        attributes=[KeyValue(key=key, value=any_value(value)) for key, value in enriched.items()],
        status=Status(code=Status.STATUS_CODE_OK),
    )
    request = ExportTraceServiceRequest(resource_spans=[ResourceSpans(
        resource=Resource(attributes=[KeyValue(
            key="service.name", value=AnyValue(string_value=service_name),
        )]),
        scope_spans=[ScopeSpans(spans=[span])],
    )])
    return request.SerializeToString()
