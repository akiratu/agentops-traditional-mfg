from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy import Uuid as SA_UUID
from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class RuntimeStatus(str, Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Agent(TimestampedModel, table=True):
    __tablename__ = "agent"

    factory_id: UUID = Field(foreign_key="factory.id", nullable=False, index=True)
    name: str = Field(nullable=False)
    purpose: str = Field(nullable=False)
    # FK to skill.id is deferred — skill table is created in Task 11.
    # The column is declared without an FK constraint here; the Alembic migration
    # in Task 11 will add the FK constraint on the live database.
    current_skill_id: UUID | None = Field(
        default=None,
        sa_column=Column(SA_UUID(as_uuid=True), nullable=True),
    )
    runtime_status: RuntimeStatus = Field(default=RuntimeStatus.PENDING, nullable=False)
    deployed_at: datetime | None = Field(default=None)


class AgentCreate(SQLModel):
    factory_id: UUID
    name: str
    purpose: str
    runtime_status: RuntimeStatus = RuntimeStatus.PENDING


class AgentRead(SQLModel):
    id: UUID
    factory_id: UUID
    name: str
    purpose: str
    current_skill_id: UUID | None
    runtime_status: RuntimeStatus
    deployed_at: datetime | None
    created_at: Any
    updated_at: Any
