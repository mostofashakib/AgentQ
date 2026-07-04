from __future__ import annotations

import asyncio
import json
import time

from starlette.types import ASGIApp, Receive, Scope, Send

from agentq.api.security import _principal_for_key
from agentq.config import settings

_WINDOW_SECONDS = 60

# Module-level state (not instance-level) so tests can reset it directly
# without reaching into Starlette's lazily-built middleware stack. Mirrors
# the module-global cache pattern already used by agentq/guardrails/settings.py.
_counts: dict[str, tuple[int, float]] = {}
_lock = asyncio.Lock()
_request_count = 0  # Track requests for lazy cleanup


def reset() -> None:
    """Clear all rate-limit counters. Tests call this to avoid one test's
    exhausted limit leaking into the next, since state is process-lifetime."""
    global _request_count
    _counts.clear()
    _request_count = 0


def _sweep_expired(now: float) -> None:
    """Remove all entries from _counts whose window has expired.
    Must be called while holding _lock. This is a lazy sweep to prevent
    unbounded memory growth in long-running processes."""
    expired_keys = [
        key
        for key, (_, window_start) in _counts.items()
        if now - window_start >= _WINDOW_SECONDS
    ]
    for key in expired_keys:
        del _counts[key]


def _key_for(scope: Scope) -> str:
    headers = dict(scope.get("headers") or [])
    api_key = headers.get(b"x-agentq-api-key", b"").decode(errors="replace")
    principal = _principal_for_key(api_key) if settings.auth_required else None
    if principal is not None:
        return principal.identity
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    """In-memory fixed-window rate limiter. Single self-hosted instance only —
    counters are per-process and do not survive a restart or synchronize
    across replicas. Revisit with a shared backend (e.g. Redis) if/when
    Phase 2 introduces horizontal scaling."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/health":
            await self.app(scope, receive, send)
            return

        key = _key_for(scope)
        now = time.monotonic()
        async with _lock:
            global _request_count
            _request_count += 1
            # Lazy sweep: every 1000 requests, remove expired entries
            if _request_count % 1000 == 0:
                _sweep_expired(now)

            count, window_start = _counts.get(key, (0, now))
            if now - window_start >= _WINDOW_SECONDS:
                count, window_start = 0, now
            count += 1
            _counts[key] = (count, window_start)
            exceeded = count > settings.rate_limit_per_minute
            retry_after = max(0, int(_WINDOW_SECONDS - (now - window_start)))

        if exceeded:
            body = json.dumps({"detail": "Rate limit exceeded"}).encode()
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", str(retry_after).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
