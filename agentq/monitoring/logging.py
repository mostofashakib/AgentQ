from __future__ import annotations

import json
import logging
from typing import Any

from agentq.config import settings
from agentq.monitoring.redaction import redact

logger = logging.getLogger("agentq.monitoring")


def log_event(
    event: str,
    *,
    trace_id: str,
    agent_run_id: str | None = None,
    session_id: str | None = None,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    if not settings.structured_logging_enabled:
        return
    payload = redact({
        "event": event,
        "trace_id": trace_id,
        "agent_run_id": agent_run_id,
        "session_id": session_id,
        "environment": settings.environment,
        **fields,
    })
    logger.log(level, json.dumps(payload, default=str, separators=(",", ":")))
