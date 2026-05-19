from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class SOPSourceType(str, Enum):
    PDF = "pdf"
    TRANSCRIPT = "transcript"
    TABLE = "table"
    QC_SPEC = "qc_spec"
    CASE_LIBRARY = "case_library"


class SOPSource(TimestampedModel, table=True):
    __tablename__ = "sop_source"

    factory_id: UUID = Field(foreign_key="factory.id", nullable=False, index=True)
    type: SOPSourceType = Field(nullable=False)
    storage_ref: str = Field(nullable=False)
    metadata_: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON)
    )
    ingested_at: datetime | None = Field(default=None)


class SOPSourceCreate(SQLModel):
    factory_id: UUID
    type: SOPSourceType
    storage_ref: str
    metadata: dict[str, Any] = {}


class SOPSourceRead(SQLModel):
    id: UUID
    factory_id: UUID
    type: SOPSourceType
    storage_ref: str
    metadata: dict[str, Any]
    ingested_at: datetime | None
    created_at: Any
    updated_at: Any

    @classmethod
    def model_validate_sop(cls, sop: SOPSource) -> "SOPSourceRead":
        return cls(
            id=sop.id,
            factory_id=sop.factory_id,
            type=sop.type,
            storage_ref=sop.storage_ref,
            metadata=sop.metadata_,
            ingested_at=sop.ingested_at,
            created_at=sop.created_at,
            updated_at=sop.updated_at,
        )
