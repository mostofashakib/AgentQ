async def test_build_client_defaults_to_anthropic(monkeypatch):
    from agentq.behaviors.llm_client import build_client, AnthropicClient

    client = build_client("anthropic", "fake-key")
    assert isinstance(client, AnthropicClient)


async def test_build_client_returns_openai_client(monkeypatch):
    from agentq.behaviors.llm_client import build_client, OpenAIClient

    client = build_client("openai", "fake-key")
    assert isinstance(client, OpenAIClient)


async def test_anthropic_client_complete_returns_text(monkeypatch):
    from agentq.behaviors.llm_client import AnthropicClient

    class _FakeContent:
        text = "hello world"

    class _FakeMsg:
        content = [_FakeContent()]

    class _FakeMessages:
        async def create(self, **kwargs):
            return _FakeMsg()

    class _FakeAnthropic:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _FakeAnthropic)

    client = AnthropicClient("fake-key")
    result = await client.complete("system", "prompt", "claude-sonnet-4-6")
    assert result == "hello world"


async def test_openai_client_complete_returns_text(monkeypatch):
    from agentq.behaviors.llm_client import OpenAIClient

    class _FakeMessage:
        content = "hello from openai"

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeResponse:
        choices = [_FakeChoice()]

    class _FakeCompletions:
        async def create(self, **kwargs):
            return _FakeResponse()

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, api_key):
            self.chat = _FakeChat()

    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", _FakeOpenAI)

    client = OpenAIClient("fake-key")
    result = await client.complete("system", "prompt", "gpt-4o-mini")
    assert result == "hello from openai"
