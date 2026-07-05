from __future__ import annotations

import argparse
import ast
import json
import operator
from datetime import UTC, datetime
from typing import Any, Callable

import httpx
from openai import OpenAI

from examples.test_agents.aop import Integration, build_json_export, build_protobuf_export


Tool = Callable[[str], str]


def web_search(query: str) -> str:
    """Use DuckDuckGo's public Instant Answer API without requiring a key."""
    response = httpx.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    results = [data.get("AbstractText", "")]
    results.extend(topic.get("Text", "") for topic in data.get("RelatedTopics", [])[:5] if isinstance(topic, dict))
    return "\n".join(item for item in results if item) or "No instant-answer results found."


_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
}


def calculate(expression: str) -> str:
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](evaluate(node.operand))
        raise ValueError("Only basic arithmetic is supported")

    return str(evaluate(ast.parse(expression, mode="eval").body))


def current_time(_: str) -> str:
    return datetime.now(UTC).isoformat()


TOOLS: dict[str, Tool] = {"web_search": web_search, "calculate": calculate, "current_time": current_time}
TOOL_ALIASES = {"calculator": "calculate", "time": "current_time"}


def normalize_tool_name(tool_name: Any) -> str:
    if isinstance(tool_name, list):
        if len(tool_name) != 1:
            raise ValueError("Model response must contain exactly one tool name")
        tool_name = tool_name[0]
    if not isinstance(tool_name, str):
        raise ValueError("Model response tool name must be a string")
    return TOOL_ALIASES.get(tool_name, tool_name)


def parse_action(content: str) -> dict:
    """Parse a model action while tolerating common Markdown JSON fences."""
    candidate = content.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        action = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response was not valid JSON") from exc
    if not isinstance(action, dict):
        raise ValueError("Model response must be a JSON object")
    return action


def build_tool_result_prompt(tool_name: str, tool_output: str) -> str:
    """Ground the final model turn in a tool result and constrain its shape."""
    return (
        f"The {tool_name} tool returned this authoritative output:\n"
        f"<tool_output>\n{tool_output}\n</tool_output>\n\n"
        "Answer the user's original request using that output. Do not call another tool. "
        "Return exactly one valid JSON object with this format and no Markdown or extra keys:\n"
        '{"final":"<answer grounded in the tool output above>"}'
    )


def build_system_prompt(required_tool: str | None = None) -> str:
    schemas = (
        'Tool call: {"tool":"web_search|calculate|current_time","input":"<tool input>"}. '
        'Final answer: {"final":"<answer>"}.'
    )
    if required_tool:
        schemas = (
            f'First response: {{"tool":"{required_tool}","input":"<tool input>"}}. '
            f'You must call {required_tool} exactly once before returning final. '
            'After receiving its output, use the final-answer format '
            '{"final":"<answer grounded in the tool output>"}.'
        )
    return (
        "You are a test agent. Return one valid JSON object only, with no Markdown or extra keys. "
        f"{schemas} Use tools when they improve accuracy."
    )


def build_required_tool_prompt(required_tool: str) -> str:
    return (
        "The required tool has not been called. Return exactly one valid JSON object "
        "with this shape and no Markdown or extra keys: "
        f'{{"tool":"{required_tool}","input":"<input derived from the original request>"}}'
    )


class AOPExporter:
    def __init__(self, endpoint: str, token: str, service_name: str, integration: Integration):
        self.endpoint = endpoint.rstrip("/") + "/v1/traces"
        self.token = token
        self.service_name = service_name
        self.integration = integration

    def emit(self, name: str, attributes: dict) -> None:
        headers = {"X-AgentQ-Agent-Token": self.token}
        if self.integration in {Integration.OPENCLAW, Integration.OTEL_PROTOBUF}:
            body = build_protobuf_export(
                integration=self.integration, service_name=self.service_name,
                name=name, attributes=attributes,
            )
            headers["Content-Type"] = "application/x-protobuf"
            response = httpx.post(self.endpoint, content=body, headers=headers, timeout=15)
        else:
            payload = build_json_export(
                integration=self.integration, service_name=self.service_name,
                name=name, attributes=attributes,
            )
            response = httpx.post(self.endpoint, json=payload, headers=headers, timeout=15)
        response.raise_for_status()


def run_agent(
    prompt: str,
    exporter: AOPExporter,
    model: str,
    ollama_url: str,
    required_tool: str | None = None,
) -> str:
    client = OpenAI(base_url=ollama_url.rstrip("/") + "/v1", api_key="ollama")
    messages = [
        {"role": "system", "content": build_system_prompt(required_tool)},
        {"role": "user", "content": prompt},
    ]
    tool_used = False

    for _ in range(6):
        completion = client.chat.completions.create(model=model, messages=messages, response_format={"type": "json_object"})
        content = completion.choices[0].message.content or "{}"
        exporter.emit("chat", {
            "gen_ai.system": "ollama", "gen_ai.operation.name": "chat",
            "gen_ai.request.model": model,
            "gen_ai.usage.input_tokens": completion.usage.prompt_tokens if completion.usage else 0,
            "gen_ai.usage.output_tokens": completion.usage.completion_tokens if completion.usage else 0,
        })
        try:
            action = parse_action(content)
        except ValueError:
            messages.extend([
                {"role": "assistant", "content": content},
                {"role": "user", "content": (
                    "Your response was malformed. Return one complete JSON object only, "
                    "using the exact tool or final schema from the system instruction."
                )},
            ])
            continue
        if final := action.get("final"):
            if required_tool and not tool_used:
                messages.extend([
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": build_required_tool_prompt(required_tool)},
                ])
                continue
            return str(final)
        try:
            tool_name = normalize_tool_name(action.get("tool", ""))
        except ValueError:
            tool_name = ""
        if required_tool and tool_name != required_tool:
            messages.extend([
                {"role": "assistant", "content": content},
                {"role": "user", "content": build_required_tool_prompt(required_tool)},
            ])
            continue
        if tool_name not in TOOLS:
            raise ValueError(f"Gemma requested unsupported tool: {tool_name}")
        tool_input = str(action.get("input", ""))
        try:
            result = TOOLS[tool_name](tool_input)
            status = "STATUS_CODE_OK"
        except Exception as exc:
            result = f"Tool error: {exc}"
            status = "STATUS_CODE_ERROR"
        exporter.emit(f"tool:{tool_name}", {
            "gen_ai.tool.name": tool_name,
            "gen_ai.tool.call.arguments": tool_input,
            "gen_ai.tool.result": result,
            "agentq.tool.status": status,
        })
        tool_used = True
        messages.extend([
            {"role": "assistant", "content": content},
            {"role": "user", "content": build_tool_result_prompt(tool_name, result)},
        ])
    raise RuntimeError("Agent exceeded its six-step limit")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Gemma AOP/1 conformance agent")
    parser.add_argument("prompt")
    parser.add_argument("--token", required=True)
    parser.add_argument("--service-name", required=True)
    parser.add_argument("--integration", choices=[item.value for item in Integration], required=True)
    parser.add_argument("--agentq-url", default="http://localhost:8000")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--model", default="gemma4:26b")
    parser.add_argument("--required-tool", choices=sorted(TOOLS))
    args = parser.parse_args()
    exporter = AOPExporter(args.agentq_url, args.token, args.service_name, Integration(args.integration))
    print(run_agent(args.prompt, exporter, args.model, args.ollama_url, args.required_tool))


if __name__ == "__main__":
    main()
