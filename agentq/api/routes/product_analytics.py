from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.api.security import require_ingest, require_viewer
from agentq.config import settings
from agentq.db.engine import get_session
from agentq.db.models import ProductEvent
from agentq.product_tracking import ProductEventInput, ProductEventTracker


router = APIRouter(prefix="/api/product-analytics", tags=["product-analytics"])


def _count_action(action: str):
    return func.sum(case((ProductEvent.action == action, 1), else_=0))


@router.post("/events", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_ingest)])
async def create_event(
    event: ProductEventInput,
    response: Response,
    tracking_opt_out: str | None = Header(default=None, alias="X-AgentQ-Tracking-Opt-Out"),
    session: AsyncSession = Depends(get_session),
):
    if tracking_opt_out and tracking_opt_out.lower() in {"1", "true", "yes"}:
        response.status_code = status.HTTP_202_ACCEPTED
        return {"tracked": False, "reason": "opted_out"}

    tracker = ProductEventTracker(
        session,
        identity_salt=settings.product_analytics_identity_salt,
        enabled=settings.product_analytics_enabled,
    )
    tracked = await tracker.track(event)
    if tracked is None:
        response.status_code = status.HTTP_202_ACCEPTED
        return {"tracked": False, "reason": "disabled"}
    await session.commit()
    return {"tracked": True, "event_id": tracked.id}


@router.get("/features", dependencies=[Depends(require_viewer)])
async def feature_summary(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(
        ProductEvent.feature,
        func.count(ProductEvent.id),
        func.count(func.distinct(ProductEvent.user_id_hash)),
        _count_action("started"),
        _count_action("completed"),
        _count_action("failed"),
        _count_action("abandoned"),
        _count_action("feedback_positive"),
        _count_action("feedback_negative"),
    ).group_by(ProductEvent.feature).order_by(func.count(ProductEvent.id).desc()))).all()

    repeated_users = select(
        ProductEvent.feature.label("feature"),
        ProductEvent.user_id_hash.label("user_id_hash"),
    ).where(
        ProductEvent.action == "completed",
        ProductEvent.user_id_hash.is_not(None),
    ).group_by(
        ProductEvent.feature, ProductEvent.user_id_hash,
    ).having(func.count(ProductEvent.id) > 1).subquery()
    repeat_counts = dict((await session.execute(select(
        repeated_users.c.feature, func.count(),
    ).group_by(repeated_users.c.feature))).all())

    summaries = []
    for feature, events, users, started, completed, failed, abandoned, positive, negative in rows:
        summaries.append({
            "feature": feature,
            "event_count": events,
            "unique_user_count": users,
            "repeat_user_count": repeat_counts.get(feature, 0),
            "started_count": started,
            "completed_count": completed,
            "failed_count": failed,
            "abandoned_count": abandoned,
            "positive_feedback_count": positive,
            "negative_feedback_count": negative,
            "completion_rate": completed / started if started else 0,
        })
    return summaries
