"""
Demo mode endpoints — only mounted when DEMO_MODE=true.

POST /api/demo/seed   — seed the DB with demo data (idempotent)
POST /api/demo/reset  — clear all demo data then re-seed
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.engine import get_session
from agentq.demo.seed import clear_demo, seed_demo
from agentq.api.security import require_admin

router = APIRouter(prefix="/api/demo", tags=["demo"], dependencies=[Depends(require_admin)])


@router.post("/seed")
async def seed(session: AsyncSession = Depends(get_session)):
    return await seed_demo(session)


@router.post("/reset")
async def reset(session: AsyncSession = Depends(get_session)):
    await clear_demo(session)
    return await seed_demo(session)
