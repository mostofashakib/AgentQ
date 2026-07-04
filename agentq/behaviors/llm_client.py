from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, system: str, prompt: str, model: str, max_tokens: int = 512) -> str:
        ...


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, system: str, prompt: str, model: str, max_tokens: int = 512) -> str:
        msg = await self._client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, base_url: str | None = None):
        import openai
        self.base_url = base_url
        options = {"api_key": api_key or "local"}
        if base_url:
            options["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**options)

    async def complete(self, system: str, prompt: str, model: str, max_tokens: int = 512) -> str:
        resp = await self._client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()


_COMPATIBLE_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "huggingface": "https://router.huggingface.co/v1",
}


def build_client(provider: str, api_key: str, base_url: str | None = None) -> LLMClient:
    if provider == "anthropic":
        return AnthropicClient(api_key)
    if provider in {"openai", "openrouter", "huggingface", "local"}:
        resolved_url = base_url or _COMPATIBLE_BASE_URLS.get(provider)
        if provider == "local" and not resolved_url:
            raise ValueError("Local provider requires a base URL")
        return OpenAIClient(api_key, resolved_url)
    raise ValueError(f"Unsupported LLM provider: {provider}")
