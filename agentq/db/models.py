from __future__ import annotations
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import BigInteger, Boolean, Float, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel, Field
from agentq.utils.time import utc_now


class Base(DeclarativeBase):
    pass


class Span(Base):
    __tablename__ = "spans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, index=True)
    span_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String)
    span_kind: Mapped[str] = mapped_column(String)
    service_name: Mapped[str] = mapped_column(String, index=True)
    start_time_unix_nano: Mapped[int] = mapped_column(BigInteger)
    end_time_unix_nano: Mapped[int] = mapped_column(BigInteger)
    duration_ms: Mapped[float] = mapped_column(Float)
    status_code: Mapped[str] = mapped_column(String, default="STATUS_CODE_UNSET")
    gen_ai_system: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gen_ai_operation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gen_ai_input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gen_ai_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gen_ai_tool_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_run_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    trace_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    agent_type: Mapped[str] = mapped_column(String, default="unknown", index=True)
    environment: Mapped[str] = mapped_column(String, default="local", index=True)
    status: Mapped[str] = mapped_column(String, default="success", index=True)
    started_at_unix_nano: Mapped[int] = mapped_column(BigInteger, default=0)
    ended_at_unix_nano: Mapped[int] = mapped_column(BigInteger, default=0)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_types: Mapped[list] = mapped_column(JSON, default=list)
    model_call_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_success_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_failure_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    terminal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, index=True)
    agent_run_id: Mapped[str] = mapped_column(String, index=True)
    evaluator: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, index=True)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    span_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    reason: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, index=True)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    span_id: Mapped[str] = mapped_column(String, index=True)
    tool_name: Mapped[str] = mapped_column(String, index=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, index=True)
    span_id: Mapped[str] = mapped_column(String, index=True)
    rule_id: Mapped[str] = mapped_column(String)
    threat_class: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    evidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chain_span_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class BehaviorCluster(Base):
    __tablename__ = "behavior_clusters"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, default="")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rubric: Mapped[list] = mapped_column(JSON, default=list)
    centroid: Mapped[list] = mapped_column(JSON, default=list)
    trace_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class BehaviorAssignment(Base):
    __tablename__ = "behavior_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, index=True)
    cluster_id: Mapped[str] = mapped_column(String, index=True)
    similarity_score: Mapped[float] = mapped_column(Float)
    assigned_at: Mapped[datetime] = mapped_column(default=utc_now)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    channels: Mapped[list] = mapped_column(JSON, default=list)
    frequency_limit: Mapped[int] = mapped_column(Integer, default=0)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String, index=True)
    trace_id: Mapped[str] = mapped_column(String)
    span_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    channel: Mapped[str] = mapped_column(String)
    fired_at: Mapped[datetime] = mapped_column(default=utc_now)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default="singleton")
    token_explosion_threshold: Mapped[int] = mapped_column(Integer, default=8000)
    excessive_tool_calls_threshold: Mapped[int] = mapped_column(Integer, default=20)
    infinite_loop_repeat_threshold: Mapped[int] = mapped_column(Integer, default=5)
    behavior_similarity_threshold: Mapped[float] = mapped_column(Float, default=0.82)
    default_alert_channel: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    llm_provider: Mapped[str] = mapped_column(String, default="anthropic")
    llm_model: Mapped[str] = mapped_column(String, default="claude-sonnet-4-6")
    llm_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# Pydantic models for ingest / inter-module data transfer

class SpanRecord(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    span_kind: str
    service_name: str
    start_time_unix_nano: int
    end_time_unix_nano: int
    duration_ms: float
    status_code: str = "STATUS_CODE_UNSET"
    gen_ai_system: Optional[str] = None
    gen_ai_operation: Optional[str] = None
    gen_ai_input_tokens: Optional[int] = None
    gen_ai_output_tokens: Optional[int] = None
    gen_ai_tool_name: Optional[str] = None
    gen_ai_finish_reasons: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)


class ClusterRecord(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    rubric: list[str] = Field(default_factory=list)
    centroid: list[float] = Field(default_factory=list)
    trace_count: int = 0
    created_at: Optional[datetime] = None


class AssignmentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    cluster_id: str
    similarity_score: float
    assigned_at: datetime = Field(default_factory=utc_now)
