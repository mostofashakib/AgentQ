from fastapi import APIRouter, Header, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.ingest.parser import parse_otlp_json, parse_otlp_protobuf
from agentq.ingest.writer import write_spans
from agentq.api.security import require_ingest
from agentq.agents import authorize_agent

router = APIRouter()


@router.post("/v1/traces")
async def receive_traces(
    request: Request,
    session: AsyncSession = Depends(get_session),
    agent_token: str | None = Header(default=None, alias="X-AgentQ-Agent-Token"),
    _principal=Depends(require_ingest),
):
    content_type = request.headers.get("content-type", "")
    if "application/x-protobuf" in content_type:
        body = await request.body()
        try:
            records = parse_otlp_protobuf(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid protobuf body")
    else:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        records = parse_otlp_json(payload)
    if not records:
        return {"accepted": 0}
    agent = await authorize_agent(session, {record.service_name for record in records}, agent_token)
    if agent is None:
        raise HTTPException(status_code=403, detail="Agent is not connected or its token is invalid")
    spans = await write_spans(session, records, analyze_behavior=True)
    return {"accepted": len(spans)}
