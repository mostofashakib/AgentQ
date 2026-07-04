# agentq/api/routes/alerts.py
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from agentq.db.engine import get_session
from agentq.db.models import AlertRule, AlertHistory
from agentq.api.alerts import worker as alert_worker_module
from agentq.api.security import require_admin, require_viewer

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertRuleBody(BaseModel):
    name: str
    conditions: dict = Field(default_factory=dict)
    channels: list[dict] = Field(default_factory=list)
    frequency_limit: int = 0
    cooldown_minutes: int = 0
    enabled: bool = True


@router.get("/rules")
async def list_rules(session: AsyncSession = Depends(get_session), _principal=Depends(require_viewer)):
    result = await session.execute(select(AlertRule).order_by(desc(AlertRule.created_at)))
    return [_rule_to_dict(r) for r in result.scalars().all()]


@router.post("/rules")
async def create_rule(
    body: AlertRuleBody,
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_admin),
):
    rule = AlertRule(
        id=str(uuid.uuid4()),
        name=body.name, conditions=body.conditions,
        channels=body.channels, frequency_limit=body.frequency_limit,
        cooldown_minutes=body.cooldown_minutes, enabled=body.enabled,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    alert_worker_module._rules_refreshed_at = None
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    body: AlertRuleBody,
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_admin),
):
    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.name = body.name
    rule.conditions = body.conditions
    rule.channels = body.channels
    rule.frequency_limit = body.frequency_limit
    rule.cooldown_minutes = body.cooldown_minutes
    rule.enabled = body.enabled
    await session.commit()
    alert_worker_module._rules_refreshed_at = None
    return _rule_to_dict(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_admin),
):
    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await session.delete(rule)
    await session.commit()
    alert_worker_module._rules_refreshed_at = None
    return {"deleted": rule_id}


@router.get("/history")
async def list_history(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    _principal=Depends(require_viewer),
):
    result = await session.execute(
        select(AlertHistory).order_by(desc(AlertHistory.fired_at)).offset(offset).limit(limit)
    )
    return [_history_to_dict(h) for h in result.scalars().all()]


def _rule_to_dict(r: AlertRule) -> dict:
    return {
        "id": r.id, "name": r.name, "conditions": r.conditions,
        "channels": r.channels, "frequency_limit": r.frequency_limit,
        "cooldown_minutes": r.cooldown_minutes, "enabled": r.enabled,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _history_to_dict(h: AlertHistory) -> dict:
    return {
        "id": h.id, "rule_id": h.rule_id, "trace_id": h.trace_id,
        "span_id": h.span_id, "channel": h.channel,
        "fired_at": h.fired_at.isoformat() if h.fired_at else None,
    }
