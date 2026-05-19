from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class SkillStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Skill(TimestampedModel, table=True):
    __tablename__ = "skill"

    agent_id: UUID = Field(foreign_key="agent.id", nullable=False, index=True)
    version: int = Field(nullable=False)
    status: SkillStatus = Field(default=SkillStatus.DRAFT, nullable=False)
    prompt: str = Field(nullable=False)
    tool_specs: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    golden_test_cases: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    sop_source_set_id: str = Field(nullable=False)
    generated_by_run_id: str | None = Field(default=None)


class SkillCreate(SQLModel):
    agent_id: UUID
    version: int
    status: SkillStatus = SkillStatus.DRAFT
    prompt: str
    tool_specs: list[dict[str, Any]] = []
    golden_test_cases: list[dict[str, Any]] = []
    sop_source_set_id: str
    generated_by_run_id: str | None = None


class SkillRead(SQLModel):
    id: UUID
    agent_id: UUID
    version: int
    status: SkillStatus
    prompt: str
    tool_specs: list[dict[str, Any]]
    golden_test_cases: list[dict[str, Any]]
    sop_source_set_id: str
    generated_by_run_id: str | None
    created_at: Any
    updated_at: Any
