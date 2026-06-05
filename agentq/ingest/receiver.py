from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.ingest.parser import parse_otlp_json
from agentq.ingest.writer import write_spans

router = APIRouter()


@router.post("/v1/traces")
async def receive_traces(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    content_type = request.headers.get("content-type", "")
    if "application/x-protobuf" in content_type:
        raise HTTPException(
            status_code=415,
            detail="Protobuf encoding not supported. Set OTEL_EXPORTER_OTLP_PROTOCOL=http/json",
        )
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    records = parse_otlp_json(payload)
    if not records:
        return {"accepted": 0}
    spans = await write_spans(session, records)
    return {"accepted": len(spans)}
