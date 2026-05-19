from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class TestSetStrategy(str, Enum):
    REPLAY_RECENT = "replay_recent"
    GOLDEN = "golden"
    MIXED = "mixed"


class RegressionVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


class RegressionRun(TimestampedModel, table=True):
    __tablename__ = "regression_run"

    skill_id_old: UUID = Field(foreign_key="skill.id", nullable=False, index=True)
    skill_id_new: UUID = Field(foreign_key="skill.id", nullable=False, index=True)
    test_set_strategy: TestSetStrategy = Field(
        default=TestSetStrategy.MIXED, nullable=False
    )
    test_case_count: int = Field(default=0, nullable=False)
    pass_count: int = Field(default=0, nullable=False)
    fail_count: int = Field(default=0, nullable=False)
    per_case_results: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    regression_findings: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    verdict: RegressionVerdict = Field(
        default=RegressionVerdict.NEEDS_REVIEW, nullable=False
    )


class RegressionRunCreate(SQLModel):
    skill_id_old: UUID
    skill_id_new: UUID
    test_set_strategy: TestSetStrategy = TestSetStrategy.MIXED
    test_case_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    per_case_results: list[dict[str, Any]] = []
    regression_findings: list[str] = []
    verdict: RegressionVerdict = RegressionVerdict.NEEDS_REVIEW


class RegressionRunRead(SQLModel):
    id: UUID
    skill_id_old: UUID
    skill_id_new: UUID
    test_set_strategy: TestSetStrategy
    test_case_count: int
    pass_count: int
    fail_count: int
    per_case_results: list[dict[str, Any]]
    regression_findings: list[str]
    verdict: RegressionVerdict
    created_at: Any
    updated_at: Any
