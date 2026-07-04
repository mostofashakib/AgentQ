from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from agentq.db.engine import get_session
from agentq.ingest.simple_report import build_span_record_from_report
from agentq.ingest.writer import write_spans

router = APIRouter(prefix="/api")


class ReportActionRequest(BaseModel):
    agent_name: str
    tool_name: str
    input: str = ""
    output: str = ""
    attributes: dict = {}


@router.post("/report")
async def report_action(body: ReportActionRequest, session: AsyncSession = Depends(get_session)):
    record = build_span_record_from_report(
        agent_name=body.agent_name,
        tool_name=body.tool_name,
        input=body.input,
        output=body.output,
        attributes=body.attributes,
    )
    await write_spans(session, [record])
    return {"accepted": True, "trace_id": record.trace_id, "span_id": record.span_id}
