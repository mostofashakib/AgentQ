from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.config import settings
from agentq.db.models import AgentRun, ApprovalRequest, EvaluationResult, MonitoringEvent, Span, Violation


async def prune_expired_telemetry(session: AsyncSession) -> None:
    cutoff = datetime.utcnow() - timedelta(days=settings.telemetry_retention_days)
    for model in (EvaluationResult, MonitoringEvent, ApprovalRequest, Violation, Span, AgentRun):
        await session.execute(delete(model).where(model.created_at < cutoff))
    await session.commit()
