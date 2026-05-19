from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class AnomalySourceType(StrEnum):
    METRIC_DRIFT = "metric_drift"
    COST_SPIKE = "cost_spike"
    HUMAN_FLAG = "human_flag"
    SCHEDULED = "scheduled"


class AnomalyStatus(StrEnum):
    NEW = "new"
    ANALYZING = "analyzing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AnomalySignal(TimestampedModel, table=True):
    __tablename__ = "anomaly_signal"

    agent_id: UUID = Field(foreign_key="agent.id", nullable=False, index=True)
    source_type: AnomalySourceType = Field(nullable=False)
    related_trace_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: AnomalyStatus = Field(default=AnomalyStatus.NEW, nullable=False)


class AnomalySignalCreate(SQLModel):
    agent_id: UUID
    source_type: AnomalySourceType
    related_trace_refs: list[str] = []
    status: AnomalyStatus = AnomalyStatus.NEW


class AnomalySignalRead(SQLModel):
    id: UUID
    agent_id: UUID
    source_type: AnomalySourceType
    related_trace_refs: list[str]
    status: AnomalyStatus
    created_at: datetime
    updated_at: datetime
