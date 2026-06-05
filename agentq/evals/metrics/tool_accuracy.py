from __future__ import annotations


def score(span_records: list) -> float:
    tool_spans = [
        s for s in span_records
        if s.gen_ai_tool_name is not None
    ]
    if not tool_spans:
        return 1.0  # no tools used = trivially accurate
    successful = sum(
        1 for s in tool_spans
        if s.status_code in ("STATUS_CODE_OK", "STATUS_CODE_UNSET")
    )
    return round(successful / len(tool_spans), 4)
