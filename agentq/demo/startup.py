from collections.abc import Callable
from typing import Any


async def seed_demo_if_enabled(*, enabled: bool, session_factory: Callable[[], Any]) -> None:
    """Seed demo records only when demo mode was explicitly enabled at startup."""
    if not enabled:
        return

    # Keep demo data and its relatively large fixtures out of normal startup.
    from agentq.demo.seed import seed_demo

    async with session_factory() as session:
        await seed_demo(session)
