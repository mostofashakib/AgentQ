from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.engine import get_session
from agentq.db.models import EvalResult

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.get("")
async def list_evals(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(EvalResult).order_by(desc(EvalResult.created_at)).offset(offset).limit(limit)
    )
    return [_e_to_dict(e) for e in result.scalars().all()]


@router.get("/{trace_id}")
async def get_eval(trace_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(EvalResult).where(EvalResult.trace_id == trace_id))
    e = result.scalars().first()
    if not e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Eval not found")
    return _e_to_dict(e)


def _e_to_dict(e: EvalResult) -> dict:
    return {
        "id": e.id,
        "trace_id": e.trace_id,
        "task_completion": e.task_completion,
        "tool_accuracy": e.tool_accuracy,
        "efficiency": e.efficiency,
        "judge_score": e.judge_score,
        "judge_rationale": e.judge_rationale,
        "judge_flagged": e.judge_flagged,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
