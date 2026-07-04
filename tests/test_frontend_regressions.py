from pathlib import Path


def test_behavior_cluster_actions_are_sibling_buttons():
    source = Path("frontend/app/(main)/behaviors/page.tsx").read_text()

    assert 'aria-expanded={expanded === cluster.id}' in source
    assert 'aria-label={`Generate rubric for ${cluster.name}`}' in source
    assert source.index('aria-expanded={expanded === cluster.id}') < source.index(
        'aria-label={`Generate rubric for ${cluster.name}`}'
    )


def test_connect_page_has_no_redundant_monitoring_choice():
    source = Path("frontend/app/(main)/connect/page.tsx").read_text()

    assert "Connect agent" in source
    assert "Observe traces" not in source
    assert "captureTraces" not in source
    assert "Behavior analysis and trace monitoring start automatically" in source
    assert "3. CONFIGURATION" in source
    assert "4. CONFIG" not in source
    assert "CONNECTED AGENTS" in source
    assert "Disconnect" in source
    assert "X-AgentQ-Agent-Token" in source


def test_sidebar_uses_concise_product_navigation():
    source = Path("frontend/components/Sidebar.tsx").read_text()
    layout = Path("frontend/app/(main)/layout.tsx").read_text()

    assert "label: 'Agents'" in source
    assert "label: 'Traces'" in source
    assert "Developed by Mostofa Shakib" not in source
    assert "'Open navigation'" in source
    assert "md:hidden" in source
    assert "hidden md:flex" in source
    assert "min-w-0" in layout
    assert "pt-14 md:pt-0" in layout


def test_primary_screens_avoid_redundant_copy_and_offer_empty_state_actions():
    traces = Path("frontend/app/(main)/traces/page.tsx").read_text()
    behaviors = Path("frontend/app/(main)/behaviors/page.tsx").read_text()
    violations = Path("frontend/app/(main)/violations/page.tsx").read_text()
    settings = Path("frontend/app/(main)/settings/page.tsx").read_text()

    assert "Live Trace Feed" not in traces
    assert "Real-time span stream from connected agents" not in traces
    assert "href=\"/connect\"" in traces
    assert "href=\"/connect\"" in behaviors
    assert "Violation Audit Log" not in violations
    assert "Guardrail thresholds, default alert channel, and connection info" not in settings
    assert "CONNECT VIA MCP OR API" not in settings


def test_run_health_has_an_actionable_empty_state():
    source = Path("frontend/app/(main)/monitoring/page.tsx").read_text()

    assert "No runs yet" in source
    assert "href=\"/connect\"" in source
    assert "Object.keys(metrics.evaluation_counts).length > 0" in source


def test_documentation_uses_current_navigation_names():
    source = Path("frontend/app/docs/page.tsx").read_text()

    assert "Connect Agent page" not in source
    assert "Live Traces feed" not in source
    assert "Developed by Mostofa Shakib" not in source


def test_settings_page_lists_all_supported_llm_providers():
    source = Path("frontend/app/(main)/settings/page.tsx").read_text()

    for provider in ("anthropic", "openai", "openrouter", "huggingface", "local"):
        assert f'value="{provider}"' in source
