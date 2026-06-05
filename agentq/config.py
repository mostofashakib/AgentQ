from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./agentq.db"
    judge_provider: str = "anthropic"
    judge_model: str = "claude-3-5-sonnet-20241022"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    openrouter_api_key: str = ""
    webhook_url: str = ""
    webhook_enabled: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
