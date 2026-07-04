from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: Literal["local", "staging", "production"] = "local"
    tracing_enabled: bool = True
    trace_sampling_rate: float = 1.0
    raw_prompt_logging_enabled: bool = False
    raw_output_logging_enabled: bool = False
    structured_logging_enabled: bool = True
    telemetry_retention_days: int = 30
    max_agent_steps: int = 50
    max_model_calls: int = 20
    max_tool_calls: int = 30
    max_retries: int = 5
    max_runtime_seconds: float = 300.0
    max_tokens_per_run: int = 100_000
    max_cost_usd_per_run: float = 10.0
    max_similar_tool_calls: int = 5
    unusual_cost_usd: float = 5.0
    unusual_latency_ms: float = 30_000.0
    unusual_output_tokens: int = 8_000
    approval_required_tools: str = (
        "send_email,delete,delete_file,drop_table,update_production,make_purchase,"
        "publish,change_permissions,privileged_exec"
    )
    database_url: str = "sqlite+aiosqlite:///./agentq.db"
    demo_database_url: str = "sqlite+aiosqlite:///./agentq_demo.db"
    demo_mode: bool = False
    judge_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    webhook_url: str = ""
    webhook_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    slack_webhook_url: str = ""
    behavior_similarity_threshold: float = 0.82

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def approval_tools(self) -> set[str]:
        return {item.strip().lower() for item in self.approval_required_tools.split(",") if item.strip()}


settings = Settings()
