from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
import uuid
from pydantic import BaseModel, Field
from agentq.utils.time import utc_now

ThreatClass = Literal["injection", "scope", "exfiltration", "behavioral", "integrity"]
Severity = Literal["low", "medium", "high", "critical"]


class ViolationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    span_id: str
    rule_id: str
    threat_class: ThreatClass
    severity: Severity
    description: str
    evidence: Optional[str] = None
    chain_span_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
