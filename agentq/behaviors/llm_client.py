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
    def __init__(self, api_key: str):
        import openai
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(self, system: str, prompt: str, model: str, max_tokens: int = 512) -> str:
        resp = await self._client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()


def build_client(provider: str, api_key: str) -> LLMClient:
    if provider == "openai":
        return OpenAIClient(api_key)
    return AnthropicClient(api_key)
