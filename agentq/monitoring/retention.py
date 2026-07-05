import asyncio
import logging
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

import agentq.db.engine as _db_engine
from agentq.config import settings
from agentq.db.models import AgentRun, ApprovalRequest, EvaluationResult, MonitoringEvent, ProductEvent, Span, Violation
from agentq.utils.time import utc_now

logger = logging.getLogger(__name__)


async def prune_expired_telemetry(session: AsyncSession) -> None:
    cutoff = utc_now() - timedelta(days=settings.telemetry_retention_days)
    for model in (EvaluationResult, MonitoringEvent, ApprovalRequest, Violation, Span, AgentRun):
        await session.execute(delete(model).where(model.created_at < cutoff))
    product_cutoff = utc_now() - timedelta(days=settings.product_analytics_retention_days)
    await session.execute(delete(ProductEvent).where(ProductEvent.created_at < product_cutoff))
    await session.commit()


async def retention_worker() -> None:
    """Prune expired telemetry on a fixed interval so long-lived servers stay pruned."""
    while True:
        await asyncio.sleep(settings.retention_interval_seconds)
        try:
            async with _db_engine.async_session() as session:
                await prune_expired_telemetry(session)
        except Exception:
            logger.exception("retention_worker prune failed")
