from __future__ import annotations
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from agentq.db.models import BehaviorCluster, BehaviorAssignment, Span
from agentq.config import settings

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are an AI observability analyst. Given summaries of agent traces that form a behavior cluster, "
    "identify 3-5 concise criteria that characterize this behavior pattern. "
    "Respond with ONLY valid JSON: "
    '{"name": "short descriptive name (3-5 words)", "criteria": ["criterion 1", "criterion 2", ...]}'
)


async def generate_rubric(session: AsyncSession, cluster_id: str) -> None:
    result = await session.execute(
        select(BehaviorCluster).where(BehaviorCluster.id == cluster_id)
    )
    cluster = result.scalars().first()
    if not cluster:
        return

    assignments = (await session.execute(
        select(BehaviorAssignment)
        .where(BehaviorAssignment.cluster_id == cluster_id)
        .limit(5)
    )).scalars().all()

    summaries: list[str] = []
    for a in assignments:
        spans = (await session.execute(
            select(Span).where(Span.trace_id == a.trace_id).limit(10)
        )).scalars().all()
        ops = []
        for s in spans:
            part = s.gen_ai_operation or s.name
            if s.gen_ai_tool_name:
                part = f"{part}:{s.gen_ai_tool_name}"
            ops.append(part)
        summaries.append(f"Trace {a.trace_id[:8]}: " + " → ".join(ops))

    if not summaries:
        return

    prompt = "Trace summaries:\n" + "\n".join(f"- {s}" for s in summaries)

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.judge_model,
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(msg.content[0].text.strip())
        cluster.rubric = data.get("criteria", [])
        cluster.name = data.get("name", cluster.name)
        cluster.description = "; ".join(data.get("criteria", []))
    except Exception:
        logger.exception("Rubric generation failed for behavior cluster %s", cluster_id)

    await session.commit()
