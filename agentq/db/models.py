from __future__ import annotations
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import BigInteger, Boolean, Float, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel, Field


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
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


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
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class BehaviorCluster(Base):
    __tablename__ = "behavior_clusters"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, default="")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rubric: Mapped[list] = mapped_column(JSON, default=list)
    centroid: Mapped[list] = mapped_column(JSON, default=list)
    trace_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class BehaviorAssignment(Base):
    __tablename__ = "behavior_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, index=True)
    cluster_id: Mapped[str] = mapped_column(String, index=True)
    similarity_score: Mapped[float] = mapped_column(Float)
    assigned_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    channels: Mapped[list] = mapped_column(JSON, default=list)
    frequency_limit: Mapped[int] = mapped_column(Integer, default=0)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String, index=True)
    trace_id: Mapped[str] = mapped_column(String)
    span_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    channel: Mapped[str] = mapped_column(String)
    fired_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


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
    gen_ai_finish_reasons: list[str] = []
    attributes: dict = {}


class ClusterRecord(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    rubric: list[str] = []
    centroid: list[float] = []
    trace_count: int = 0
    created_at: Optional[datetime] = None


class AssignmentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    cluster_id: str
    similarity_score: float
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
