from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = re.compile(
    r"password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"authorization|cookie|session[_-]?cookie|token|credit[_-]?card|card[_-]?number|cvv|ssn|government[_-]?id",
    re.IGNORECASE,
)
_PATTERNS = [
    re.compile(r"(?i)\b(?:sk|pk|api)[-_][a-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\bBearer\s+[a-z0-9._~+/-]{8,}=*"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
]


def redact_text(value: str) -> str:
    redacted = value
    for pattern in _PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact(value: Any, key: str = "") -> Any:
    """Recursively redact secrets and common PII before persistence or logging."""
    if _SENSITIVE_KEYS.search(key):
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value


def sanitize_span_attributes(attributes: dict[str, Any], allow_prompt: bool, allow_output: bool) -> dict[str, Any]:
    safe = dict(attributes)
    prompt_keys = {"gen_ai.prompt", "gen_ai.input.messages", "input.value"}
    output_keys = {"gen_ai.completion", "gen_ai.output.messages", "gen_ai.tool.result", "output.value"}
    if not allow_prompt:
        for key in prompt_keys & safe.keys():
            safe[key] = "[OMITTED]"
    if not allow_output:
        for key in output_keys & safe.keys():
            safe[key] = "[OMITTED]"
    return redact(safe)
