from agentq.config import settings
from agentq.evals.judges.base import AbstractJudge


def get_judge() -> AbstractJudge:
    provider = settings.judge_provider.lower()
    if provider == "anthropic":
        from agentq.evals.judges.anthropic import AnthropicJudge
        return AnthropicJudge()
    if provider == "openai":
        from agentq.evals.judges.openai import OpenAIJudge
        return OpenAIJudge()
    if provider == "ollama":
        from agentq.evals.judges.ollama import OllamaJudge
        return OllamaJudge()
    if provider == "openrouter":
        from agentq.evals.judges.openrouter import OpenRouterJudge
        return OpenRouterJudge()
    raise ValueError(f"Unknown judge provider: {provider!r}. Choose from: anthropic, openai, ollama, openrouter")
