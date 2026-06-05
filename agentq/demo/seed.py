"""
Demo seeding logic — writes realistic sample data directly to the database.

Idempotent: seed_demo() is a no-op if demo spans already exist.
reset_demo() clears all demo data then re-seeds.
"""

import math
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from agentq.db.models import (
    AlertRule,
    BehaviorAssignment,
    BehaviorCluster,
    Span,
    Violation,
)
from agentq.demo.data import ALERT_RULES, CLUSTERS, DEMO_TRACE_IDS, SCENARIOS

_DEMO_ALERT_IDS = {r["id"] for r in ALERT_RULES}
_DEMO_CLUSTER_IDS = {c["id"] for c in CLUSTERS.values()}


def _centroid(seed: int, dim: int = 384) -> list[float]:
    v = [math.sin(i * 0.7 + seed * 1.3) * math.cos(i * 0.31 + seed * 0.2) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / norm, 6) for x in v]


def _utc(minutes_ago: float) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes_ago)


async def clear_demo(session: AsyncSession) -> None:
    await session.execute(delete(Span).where(Span.trace_id.in_(DEMO_TRACE_IDS)))
    await session.execute(delete(Violation).where(Violation.trace_id.in_(DEMO_TRACE_IDS)))
    await session.execute(
        delete(BehaviorAssignment).where(BehaviorAssignment.trace_id.in_(DEMO_TRACE_IDS))
    )
    await session.execute(
        delete(BehaviorCluster).where(BehaviorCluster.id.in_(_DEMO_CLUSTER_IDS))
    )
    await session.execute(delete(AlertRule).where(AlertRule.id.in_(_DEMO_ALERT_IDS)))
    await session.commit()


async def seed_demo(session: AsyncSession) -> dict:
    existing = (
        await session.execute(select(Span).where(Span.trace_id.in_(DEMO_TRACE_IDS)).limit(1))
    ).scalars().first()
    if existing:
        return {"status": "already_seeded"}

    now_ns = time.time_ns()

    # ── Behavior clusters ────────────────────────────────────────────────────────
    cluster_seed = {"information-retrieval": 1, "automated-execution": 2, "conversational": 3}
    for idx, (key, c) in enumerate(CLUSTERS.items()):
        session.add(BehaviorCluster(
            id=c["id"],
            name=c["name"],
            description=c["description"],
            rubric=c["rubric"],
            centroid=_centroid(cluster_seed[key]),
            trace_count=c["trace_count"],
            created_at=_utc(90),
        ))

    # ── Spans, violations, and behavior assignments per scenario ─────────────────
    for scenario in SCENARIOS:
        trace_id = scenario["trace_id"]
        service = scenario["service"]
        offset_min = scenario["scenario_offset_min"]
        base_ns = now_ns - int(offset_min * 60 * 1_000_000_000)

        for span_data in scenario["spans"]:
            start_ns = base_ns + int(span_data["offset_ms"] * 1_000_000)
            end_ns = start_ns + int(span_data["duration_ms"] * 1_000_000)
            session.add(Span(
                id=str(uuid.uuid4()),
                trace_id=trace_id,
                span_id=span_data["span_id"],
                parent_span_id=span_data.get("parent_span_id"),
                name=span_data["name"],
                span_kind=span_data["span_kind"],
                service_name=service,
                start_time_unix_nano=start_ns,
                end_time_unix_nano=end_ns,
                duration_ms=span_data["duration_ms"],
                status_code="STATUS_CODE_OK",
                gen_ai_system=span_data.get("gen_ai_system"),
                gen_ai_operation=span_data.get("gen_ai_operation"),
                gen_ai_input_tokens=span_data.get("gen_ai_input_tokens"),
                gen_ai_output_tokens=span_data.get("gen_ai_output_tokens"),
                gen_ai_tool_name=span_data.get("gen_ai_tool_name"),
                attributes=span_data.get("attributes", {}),
                created_at=datetime.utcfromtimestamp(start_ns / 1e9),
            ))

        for viol_data in scenario["violations"]:
            session.add(Violation(
                id=str(uuid.uuid4()),
                trace_id=trace_id,
                span_id=viol_data["span_id"],
                rule_id=viol_data["rule_id"],
                threat_class=viol_data["threat_class"],
                severity=viol_data["severity"],
                description=viol_data["description"],
                evidence=viol_data.get("evidence"),
                chain_span_ids=[],
                created_at=_utc(offset_min),
            ))

        cluster_id = CLUSTERS[scenario["cluster_key"]]["id"]
        session.add(BehaviorAssignment(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            cluster_id=cluster_id,
            similarity_score=scenario["similarity_score"],
            assigned_at=_utc(offset_min - 0.5),
        ))

    # ── Alert rules ──────────────────────────────────────────────────────────────
    for rule in ALERT_RULES:
        session.add(AlertRule(
            id=rule["id"],
            name=rule["name"],
            conditions=rule["conditions"],
            channels=rule["channels"],
            frequency_limit=rule["frequency_limit"],
            cooldown_minutes=rule["cooldown_minutes"],
            enabled=rule["enabled"],
            created_at=_utc(120),
        ))

    await session.commit()
    return {
        "status": "seeded",
        "traces": len(SCENARIOS),
        "violations": sum(len(s["violations"]) for s in SCENARIOS),
        "clusters": len(CLUSTERS),
        "alert_rules": len(ALERT_RULES),
    }
