from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from agentq.db.engine import get_session
from agentq.ingest.simple_report import build_span_record_from_report
from agentq.ingest.writer import write_spans
from agentq.api.security import require_ingest
from agentq.agents import authorize_agent

router = APIRouter(prefix="/api")


class ReportActionRequest(BaseModel):
    agent_name: str
    tool_name: str
    input: str = ""
    output: str = ""
    attributes: dict = Field(default_factory=dict)


@router.post("/report")
async def report_action(
    body: ReportActionRequest,
    session: AsyncSession = Depends(get_session),
    agent_token: str | None = Header(default=None, alias="X-AgentQ-Agent-Token"),
    _principal=Depends(require_ingest),
):
    record = build_span_record_from_report(
        agent_name=body.agent_name,
        tool_name=body.tool_name,
        input=body.input,
        output=body.output,
        attributes=body.attributes,
    )
    agent = await authorize_agent(session, {body.agent_name}, agent_token)
    if agent is None:
        raise HTTPException(status_code=403, detail="Agent is not connected or its token is invalid")
    await write_spans(session, [record], analyze_behavior=True)
    return {"accepted": True, "trace_id": record.trace_id, "span_id": record.span_id}
