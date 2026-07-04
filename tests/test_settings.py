import pytest


async def test_get_app_settings_creates_default_row_on_first_call():
    from agentq.guardrails import settings as guardrail_settings

    guardrail_settings.invalidate_cache()
    row = await guardrail_settings.get_app_settings()
    assert row.token_explosion_threshold == 8000
    assert row.excessive_tool_calls_threshold == 20
    assert row.infinite_loop_repeat_threshold == 5
    assert row.behavior_similarity_threshold == pytest.approx(0.82)
    assert row.default_alert_channel is None


async def test_get_app_settings_is_cached_until_invalidated():
    from agentq.guardrails import settings as guardrail_settings
    import agentq.db.engine as _db_engine
    from sqlalchemy import update
    from agentq.db.models import AppSettings

    guardrail_settings.invalidate_cache()
    first = await guardrail_settings.get_app_settings()
    assert first.token_explosion_threshold == 8000

    # Mutate the DB row directly, bypassing the cache-invalidating API route
    async with _db_engine.async_session() as session:
        await session.execute(
            update(AppSettings).where(AppSettings.id == "singleton").values(token_explosion_threshold=9999)
        )
        await session.commit()

    # Cache still holds the old value (no invalidate_cache() call)
    second = await guardrail_settings.get_app_settings()
    assert second.token_explosion_threshold == 8000

    guardrail_settings.invalidate_cache()
    third = await guardrail_settings.get_app_settings()
    assert third.token_explosion_threshold == 9999


from httpx import AsyncClient, ASGITransport
from agentq.api.app import app


async def test_get_settings_endpoint_returns_defaults():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["token_explosion_threshold"] == 8000
    assert body["default_alert_channel"] is None


async def test_put_settings_updates_only_provided_fields():
    from agentq.guardrails import settings as guardrail_settings

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.put("/api/settings", json={"token_explosion_threshold": 5000})
    assert r.status_code == 200
    body = r.json()
    assert body["token_explosion_threshold"] == 5000
    assert body["excessive_tool_calls_threshold"] == 20  # unchanged

    guardrail_settings.invalidate_cache()
    row = await guardrail_settings.get_app_settings()
    assert row.token_explosion_threshold == 5000
