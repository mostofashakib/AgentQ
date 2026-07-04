from pathlib import Path


def test_behavior_cluster_actions_are_sibling_buttons():
    source = Path("frontend/app/(main)/behaviors/page.tsx").read_text()

    assert 'aria-expanded={expanded === cluster.id}' in source
    assert 'aria-label={`Generate rubric for ${cluster.name}`}' in source
    assert source.index('aria-expanded={expanded === cluster.id}') < source.index(
        'aria-label={`Generate rubric for ${cluster.name}`}'
    )


def test_connect_page_requires_explicit_authorization_and_monitoring_choices():
    source = Path("frontend/app/(main)/connect/page.tsx").read_text()

    assert "Connect and authorize agent" in source
    assert "Observe traces" in source
    assert "Behavior analysis is always enabled" in source
    assert "CONNECTED AGENTS" in source
    assert "Disconnect" in source
    assert "X-AgentQ-Agent-Token" in source


def test_settings_page_lists_all_supported_llm_providers():
    source = Path("frontend/app/(main)/settings/page.tsx").read_text()

    for provider in ("anthropic", "openai", "openrouter", "huggingface", "local"):
        assert f'value="{provider}"' in source
