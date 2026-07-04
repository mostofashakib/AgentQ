from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.config import settings
from agentq.db.models import AgentRun, ApprovalRequest, EvaluationResult, MonitoringEvent, ProductEvent, Span, Violation
from agentq.utils.time import utc_now


async def prune_expired_telemetry(session: AsyncSession) -> None:
    cutoff = utc_now() - timedelta(days=settings.telemetry_retention_days)
    for model in (EvaluationResult, MonitoringEvent, ApprovalRequest, Violation, Span, AgentRun):
        await session.execute(delete(model).where(model.created_at < cutoff))
    product_cutoff = utc_now() - timedelta(days=settings.product_analytics_retention_days)
    await session.execute(delete(ProductEvent).where(ProductEvent.created_at < product_cutoff))
    await session.commit()
