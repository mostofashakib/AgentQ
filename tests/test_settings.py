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


async def test_get_settings_endpoint_seeds_from_env_default_on_first_creation(monkeypatch):
    """GET /api/settings, hit before get_app_settings() has ever created the
    row, must still seed behavior_similarity_threshold from
    agentq.config.settings rather than falling back to the hardcoded column
    default (0.82). Regression test for the dual get-or-create bug."""
    from agentq.guardrails import settings as guardrail_settings
    from agentq.config import settings as env_settings

    # Force a fresh lookup against the (fresh, per-test) in-memory DB instead
    # of returning a cached row from a previous test.
    guardrail_settings.invalidate_cache()
    monkeypatch.setattr(env_settings, "behavior_similarity_threshold", 0.55)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["behavior_similarity_threshold"] == pytest.approx(0.55)


async def test_get_app_settings_seeds_llm_fields_from_env_on_first_creation(monkeypatch):
    from agentq.guardrails import settings as guardrail_settings
    from agentq.config import settings as env_settings

    guardrail_settings.invalidate_cache()
    monkeypatch.setattr(env_settings, "judge_model", "claude-sonnet-4-6")
    monkeypatch.setattr(env_settings, "anthropic_api_key", "sk-ant-test-key")

    row = await guardrail_settings.get_app_settings()

    assert row.llm_provider == "anthropic"
    assert row.llm_model == "claude-sonnet-4-6"
    assert row.llm_api_key == "sk-ant-test-key"


async def test_get_app_settings_seeds_none_llm_api_key_when_env_key_empty(monkeypatch):
    from agentq.guardrails import settings as guardrail_settings
    from agentq.config import settings as env_settings

    guardrail_settings.invalidate_cache()
    monkeypatch.setattr(env_settings, "anthropic_api_key", "")

    row = await guardrail_settings.get_app_settings()

    assert row.llm_api_key is None
