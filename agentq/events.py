# agentq/events.py
from __future__ import annotations
import asyncio
from typing import Literal
from pydantic import BaseModel
from agentq.db.models import SpanRecord
from agentq.guardrails.models import ViolationRecord


class ViolationAlertEvent(BaseModel):
    type: Literal["violation"] = "violation"
    violation: ViolationRecord


class BehaviorAlertEvent(BaseModel):
    type: Literal["behavior"] = "behavior"
    cluster_id: str
    trace_id: str
    similarity_score: float


AlertEvent = ViolationAlertEvent | BehaviorAlertEvent

span_queue: asyncio.Queue[SpanRecord] = asyncio.Queue()
behavior_span_queue: asyncio.Queue[SpanRecord] = asyncio.Queue()
trace_complete_queue: asyncio.Queue[list[SpanRecord]] = asyncio.Queue()
alert_event_queue: asyncio.Queue[AlertEvent] = asyncio.Queue()
