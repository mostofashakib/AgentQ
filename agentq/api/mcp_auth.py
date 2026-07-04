from __future__ import annotations

import json

from starlette.types import ASGIApp, Receive, Scope, Send

from agentq.api.security import _principal_for_key
from agentq.config import settings


class MCPAuthMiddleware:
    """Gates the MCP mount with the same shared-secret scheme as REST routes.

    FastMCP's app is a plain Starlette ASGI app mounted at /mcp — it has no
    FastAPI Depends() to hang auth off of, so this wraps it directly, one
    layer up, before any request reaches it. Any valid key of any tier
    (ingest/viewer/admin) is accepted — an MCP-connected agent needs
    report_action (ingest-level write) and check_action/get_violations
    (read) together to function as a single client.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.auth_required:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        api_key = headers.get(b"x-agentq-api-key", b"").decode()
        if _principal_for_key(api_key) is None:
            body = json.dumps({"detail": "A valid API key is required"}).encode()
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"application/json")],
            })
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
