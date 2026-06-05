from agentq.guardrails.engine import VerifierEngine
from agentq.guardrails.rules import injection, scope, exfiltration, behavioral, integrity


def build_engine() -> VerifierEngine:
    engine = VerifierEngine()

    engine.register("injection.user_content", injection.user_content_injection)
    engine.register("injection.system_prompt_override", injection.system_prompt_override)
    engine.register("injection.indirect_via_retrieval", injection.indirect_injection_via_retrieval)
    engine.register("injection.role_confusion", injection.role_confusion_attack)

    engine.register("scope.high_risk_tool", scope.high_risk_tool_call)
    engine.register("scope.unsanctioned_tool", scope.unsanctioned_external_call)
    engine.register("scope.excessive_tool_calls", scope.excessive_tool_calls)
    engine.register("scope.destructive_without_confirmation", scope.destructive_action_without_confirmation)

    engine.register("exfiltration.url_in_output", exfiltration.url_in_output)
    engine.register("exfiltration.base64_in_output", exfiltration.base64_in_output)
    engine.register("exfiltration.sensitive_key_in_output", exfiltration.sensitive_key_in_output)
    engine.register("exfiltration.pii_in_output", exfiltration.pii_in_output)
    engine.register("exfiltration.outbound_http", exfiltration.outbound_http_tool)

    engine.register("behavioral.goal_drift", behavioral.goal_drift)
    engine.register("behavioral.infinite_loop", behavioral.infinite_loop_detection)
    engine.register("behavioral.hallucinated_tool", behavioral.hallucinated_tool)
    engine.register("behavioral.token_explosion", behavioral.token_explosion)

    engine.register("integrity.time_inversion", integrity.span_time_inversion)
    engine.register("integrity.missing_service_name", integrity.missing_service_name)
    engine.register("integrity.missing_gen_ai_attrs", integrity.model_call_missing_gen_ai_attrs)
    engine.register("integrity.empty_trace_id", integrity.empty_trace_id)

    return engine
