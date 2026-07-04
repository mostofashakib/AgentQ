import pytest
import uuid
from datetime import datetime
from agentq.db.models import (
    BehaviorCluster, BehaviorAssignment, AlertRule, AlertHistory,
    ClusterRecord, AssignmentRecord,
)


async def test_behavior_cluster_table_exists():
    from agentq.db.engine import async_session
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(BehaviorCluster))
        assert result.scalars().all() == []


async def test_behavior_assignment_table_exists():
    from agentq.db.engine import async_session
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(BehaviorAssignment))
        assert result.scalars().all() == []


async def test_alert_rule_table_exists():
    from agentq.db.engine import async_session
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(AlertRule))
        assert result.scalars().all() == []


async def test_alert_history_table_exists():
    from agentq.db.engine import async_session
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(AlertHistory))
        assert result.scalars().all() == []


async def test_behavior_cluster_insert():
    from agentq.db.engine import async_session
    from sqlalchemy import select
    cluster_id = str(uuid.uuid4())
    async with async_session() as session:
        session.add(BehaviorCluster(
            id=cluster_id, name="Behavior-1",
            centroid=[0.1] * 384, trace_count=1,
        ))
        await session.commit()
    async with async_session() as session:
        result = await session.execute(
            select(BehaviorCluster).where(BehaviorCluster.id == cluster_id)
        )
        c = result.scalars().first()
    assert c is not None
    assert c.name == "Behavior-1"
    assert c.trace_count == 1


def test_cluster_record_pydantic():
    r = ClusterRecord(id="c1", name="B-1", trace_count=3)
    assert r.rubric == []
    assert r.centroid == []


def test_engine_uses_demo_database_when_demo_mode_enabled(monkeypatch):
    import importlib
    import agentq.config as config_module

    monkeypatch.setattr(config_module.settings, "demo_mode", True)
    import agentq.db.engine as engine_module
    importlib.reload(engine_module)
    assert "agentq_demo.db" in str(engine_module.engine.url)

    monkeypatch.setattr(config_module.settings, "demo_mode", False)
    importlib.reload(engine_module)
    assert "agentq_demo.db" not in str(engine_module.engine.url)
    # restore the module to its normal (non-demo) state for other tests
    monkeypatch.setattr(config_module.settings, "demo_mode", False)
    importlib.reload(engine_module)
