from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.ingest.parser import parse_otlp_json, parse_otlp_protobuf
from agentq.ingest.writer import write_spans
from agentq.api.security import require_ingest

router = APIRouter()


@router.post("/v1/traces")
async def receive_traces(
    request: Request,
    session: AsyncSession = Depends(get_session),
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
    spans = await write_spans(session, records)
    return {"accepted": len(spans)}
