from unittest.mock import AsyncMock, Mock


async def test_demo_seed_does_not_open_session_when_disabled():
    from agentq.demo.startup import seed_demo_if_enabled

    session_factory = Mock()

    await seed_demo_if_enabled(enabled=False, session_factory=session_factory)

    session_factory.assert_not_called()


async def test_demo_seed_runs_when_explicitly_enabled(monkeypatch):
    from agentq.demo import seed, startup

    seed_demo = AsyncMock()
    monkeypatch.setattr(seed, "seed_demo", seed_demo)

    class SessionContext:
        async def __aenter__(self):
            return "session"

        async def __aexit__(self, *_args):
            return None

    session_factory = Mock(return_value=SessionContext())

    await startup.seed_demo_if_enabled(enabled=True, session_factory=session_factory)

    session_factory.assert_called_once_with()
    seed_demo.assert_awaited_once_with("session")
