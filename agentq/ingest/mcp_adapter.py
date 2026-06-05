"""
Normalize Model Context Protocol (MCP) span attributes into the AgentQ
standard GenAI attribute schema so existing guardrail rules and eval
metrics apply to MCP-instrumented agents without any changes.

MCP spans are identified by the presence of any `mcp.*` attribute.
"""

from typing import Any


_MCP_OPERATION_MAP = {
    "tools/call": "tool_use",
    "tools/list": "list_tools",
    "resources/read": "read_resource",
    "resources/list": "list_resources",
    "prompts/get": "get_prompt",
    "prompts/list": "list_prompts",
    "sampling/createMessage": "chat",
}


def is_mcp_span(attrs: dict[str, Any]) -> bool:
    return any(k.startswith("mcp.") for k in attrs)


def normalize_mcp_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    """Merge MCP-specific attributes into GenAI equivalents in-place."""
    out = dict(attrs)

    server = attrs.get("mcp.server.name")
    if server and "gen_ai.system" not in out:
        out["gen_ai.system"] = f"mcp:{server}"

    method = attrs.get("mcp.method", "")
    if method and "gen_ai.operation.name" not in out:
        out["gen_ai.operation.name"] = _MCP_OPERATION_MAP.get(method, method)

    tool_name = attrs.get("mcp.tool.name")
    if tool_name and "gen_ai.tool.name" not in out:
        out["gen_ai.tool.name"] = tool_name

    tool_input = attrs.get("mcp.tool.input")
    if tool_input and "gen_ai.tool.call.arguments" not in out:
        out["gen_ai.tool.call.arguments"] = tool_input

    tool_output = attrs.get("mcp.tool.output")
    if tool_output and "gen_ai.tool.result" not in out:
        out["gen_ai.tool.result"] = tool_output

    # Map MCP completion / prompt to GenAI equivalents for guardrail inspection
    prompt = attrs.get("mcp.prompt.content") or attrs.get("mcp.request.params")
    if prompt and "gen_ai.prompt" not in out:
        out["gen_ai.prompt"] = str(prompt)

    result = attrs.get("mcp.response.result")
    if result and "gen_ai.completion" not in out:
        out["gen_ai.completion"] = str(result)

    protocol = attrs.get("mcp.protocol.version")
    if protocol:
        out["mcp.protocol.version"] = protocol

    return out
