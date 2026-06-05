# tests/alerts/test_routes.py
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from agentq.api.app import app
from agentq.db.models import AlertHistory
import agentq.db.engine as _db_engine


async def test_create_alert_rule():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/alerts/rules", json={
            "name": "High Severity",
            "conditions": {"severity": "high"},
            "channels": [{"type": "webhook", "url": "http://example.com/hook"}],
            "frequency_limit": 5,
            "cooldown_minutes": 10,
            "enabled": True,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "High Severity"
    assert data["conditions"]["severity"] == "high"
    assert "id" in data


async def test_list_alert_rules():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/alerts/rules", json={
            "name": "Rule A", "conditions": {}, "channels": [],
            "frequency_limit": 0, "cooldown_minutes": 0, "enabled": True,
        })
        resp = await client.get("/api/alerts/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert any(r["name"] == "Rule A" for r in rules)


async def test_update_alert_rule():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post("/api/alerts/rules", json={
            "name": "Old Name", "conditions": {}, "channels": [],
            "frequency_limit": 0, "cooldown_minutes": 0, "enabled": True,
        })
        rule_id = create.json()["id"]

        resp = await client.put(f"/api/alerts/rules/{rule_id}", json={
            "name": "New Name", "conditions": {"severity": "critical"},
            "channels": [], "frequency_limit": 3, "cooldown_minutes": 5, "enabled": False,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["enabled"] is False


async def test_delete_alert_rule():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post("/api/alerts/rules", json={
            "name": "Delete Me", "conditions": {}, "channels": [],
            "frequency_limit": 0, "cooldown_minutes": 0, "enabled": True,
        })
        rule_id = create.json()["id"]
        del_resp = await client.delete(f"/api/alerts/rules/{rule_id}")
        assert del_resp.status_code == 200
        list_resp = await client.get("/api/alerts/rules")
    assert not any(r["id"] == rule_id for r in list_resp.json())


async def test_list_alert_history():
    async with _db_engine.async_session() as session:
        session.add(AlertHistory(
            rule_id=str(uuid.uuid4()), trace_id="t1",
            span_id="s1", channel="webhook",
        ))
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/alerts/history")

    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    assert history[0]["channel"] == "webhook"
