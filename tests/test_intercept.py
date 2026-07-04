async def test_check_action_detects_high_risk_tool():
    from agentq.guardrails.intercept import check_action

    violations = await check_action(
        trace_id="t1", span_id="s1", tool_name="exec_command", service_name="agent-x",
    )
    rule_ids = [v.rule_id for v in violations]
    assert "scope.high_risk_tool" in rule_ids


async def test_check_action_no_violations_for_safe_tool():
    from agentq.guardrails.intercept import check_action

    violations = await check_action(
        trace_id="t1", span_id="s1", tool_name="get_weather", service_name="agent-x",
    )
    rule_ids = [v.rule_id for v in violations]
    assert "scope.high_risk_tool" not in rule_ids
    assert not any(rid.startswith(("injection.", "exfiltration.", "scope.", "behavioral.")) for rid in rule_ids)


async def test_check_action_passes_through_attributes():
    from agentq.guardrails.intercept import check_action

    violations = await check_action(
        trace_id="t1", span_id="s1", tool_name="delete_file", service_name="agent-x",
        attributes={"agentq.user_confirmed": False},
    )
    rule_ids = [v.rule_id for v in violations]
    assert "scope.destructive_without_confirmation" in rule_ids
