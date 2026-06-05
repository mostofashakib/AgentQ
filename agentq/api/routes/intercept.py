"""
Pre-execution tool intercept endpoint.

Agents call POST /api/intercept BEFORE executing a tool. AgentQ runs the
guardrail engine against a synthetic SpanRecord and returns an allow/deny
decision immediately so the agent can halt before side effects occur.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any
from agentq.db.models import SpanRecord
from agentq.guardrails.registry import build_engine
from agentq.guardrails.models import ViolationRecord

router = APIRouter(prefix="/api")

_engine = build_engine()


class InterceptRequest(BaseModel):
    trace_id: str
    span_id: str
    tool_name: str
    service_name: str = "unknown"
    attributes: dict[str, Any] = {}


class InterceptResponse(BaseModel):
    allowed: bool
    rule_id: str | None = None
    reason: str | None = None
    violations: list[dict] = []


@router.post("/intercept", response_model=InterceptResponse)
async def intercept_tool_call(req: InterceptRequest) -> InterceptResponse:
    """
    Run guardrail checks before a tool executes. Returns immediately.

    Usage (Python):
        resp = httpx.post("http://localhost:8000/api/intercept", json={
            "trace_id": current_trace_id,
            "span_id": new_span_id,
            "tool_name": "send_email",
            "attributes": {"agentq.user_confirmed": False}
        })
        if not resp.json()["allowed"]:
            raise ToolBlockedError(resp.json()["reason"])
    """
    synthetic = SpanRecord(
        trace_id=req.trace_id,
        span_id=req.span_id,
        name=f"tool:{req.tool_name}",
        span_kind="CLIENT",
        service_name=req.service_name,
        start_time_unix_nano=0,
        end_time_unix_nano=0,
        duration_ms=0.0,
        gen_ai_tool_name=req.tool_name,
        attributes={**req.attributes, "gen_ai.tool.name": req.tool_name},
    )

    violations: list[ViolationRecord] = await _engine.run_all(synthetic)

    return InterceptResponse(
        allowed=True,
        violations=[v.model_dump() for v in violations],
    )
