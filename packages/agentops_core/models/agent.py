from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class RuntimeStatus(StrEnum):
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
    current_skill_id: UUID | None = Field(default=None, foreign_key="skill.id")
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
    created_at: datetime
    updated_at: datetime


class AgentCurrentSkillUpdate(SQLModel):
    current_skill_id: UUID | None
