from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./agentq.db"
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


settings = Settings()
