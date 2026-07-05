import pytest

from examples.test_agents.gemma_agent import (
    build_system_prompt,
    build_required_tool_prompt,
    build_tool_result_prompt,
    calculate,
    normalize_tool_name,
    parse_action,
)


def test_parse_action_accepts_json_code_fence():
    assert parse_action('```json\n{"tool":"calculate","input":"2+2"}\n```') == {
        "tool": "calculate",
        "input": "2+2",
    }


def test_parse_action_rejects_truncated_json():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_action('{"tool":"web_search","input":"OpenTele')


@pytest.mark.parametrize("expression", ["__import__('os').system('echo unsafe')", "open('/tmp/x')", "2 // 1"])
def test_calculator_rejects_code_and_unsupported_operators(expression):
    with pytest.raises(ValueError, match="basic arithmetic"):
        calculate(expression)


def test_natural_calculator_alias_is_normalized():
    assert normalize_tool_name("calculator") == "calculate"


def test_tool_result_prompt_includes_output_and_strict_response_format():
    prompt = build_tool_result_prompt("calculate", "391")

    assert "391" in prompt
    assert '"final":"<answer grounded in the tool output above>"' in prompt
    assert "one valid JSON object" in prompt
    assert "Do not call another tool" in prompt


def test_system_prompt_requires_configured_tool_before_final_answer():
    prompt = build_system_prompt("calculate")

    assert '"tool":"calculate","input":"<tool input>"' in prompt
    assert "must call calculate exactly once before returning final" in prompt


def test_single_item_tool_name_list_is_normalized():
    assert normalize_tool_name(["current_time"]) == "current_time"


def test_multiple_tool_names_are_rejected():
    with pytest.raises(ValueError, match="one tool name"):
        normalize_tool_name(["calculate", "current_time"])


def test_required_tool_retry_prompt_contains_exact_schema():
    prompt = build_required_tool_prompt("web_search")

    assert '"tool":"web_search","input":"<input derived from the original request>"' in prompt
