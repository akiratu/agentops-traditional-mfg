from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class SuggestedFixType(StrEnum):
    PROMPT_CHANGE = "prompt_change"
    ADD_SKILL = "add_skill"
    SUPPLEMENT_SOP = "supplement_sop"
    SWAP_MODEL = "swap_model"
    RETRAINING = "retraining"


class RCAFindingStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AUTO_APPLIED = "auto_applied"


class RCAFinding(TimestampedModel, table=True):
    __tablename__ = "rca_finding"

    anomaly_signal_id: UUID = Field(
        foreign_key="anomaly_signal.id", nullable=False, index=True
    )
    root_cause_summary: str = Field(nullable=False)
    evidence: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    suggested_fix_type: SuggestedFixType = Field(nullable=False)
    suggested_fix_payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    confidence_score: float = Field(default=0.0, nullable=False)
    status: RCAFindingStatus = Field(default=RCAFindingStatus.PROPOSED, nullable=False)


class RCAFindingCreate(SQLModel):
    anomaly_signal_id: UUID
    root_cause_summary: str
    evidence: dict[str, Any] = {}
    suggested_fix_type: SuggestedFixType
    suggested_fix_payload: dict[str, Any] = {}
    confidence_score: float = 0.0
    status: RCAFindingStatus = RCAFindingStatus.PROPOSED


class RCAFindingRead(SQLModel):
    id: UUID
    anomaly_signal_id: UUID
    root_cause_summary: str
    evidence: dict[str, Any]
    suggested_fix_type: SuggestedFixType
    suggested_fix_payload: dict[str, Any]
    confidence_score: float
    status: RCAFindingStatus
    created_at: datetime
    updated_at: datetime


class RCAFindingStatusUpdate(SQLModel):
    status: RCAFindingStatus
