from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from agentops_core.models.base import TimestampedModel


class DeploymentType(str, Enum):
    ON_PREM = "on_prem"
    PRIVATE_CLOUD = "private_cloud"


class Factory(TimestampedModel, table=True):
    __tablename__ = "factory"

    name: str = Field(index=True, nullable=False)
    deployment_type: DeploymentType = Field(
        default=DeploymentType.ON_PREM, nullable=False
    )
    langfuse_endpoint: str | None = Field(default=None)
    langfuse_project_id: str | None = Field(default=None)
    contact_info: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    kpi_targets: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class FactoryCreate(SQLModel):
    name: str
    deployment_type: DeploymentType = DeploymentType.ON_PREM
    langfuse_endpoint: str | None = None
    langfuse_project_id: str | None = None
    contact_info: dict[str, Any] | None = None
    kpi_targets: dict[str, Any] | None = None


class FactoryRead(SQLModel):
    id: UUID
    name: str
    deployment_type: DeploymentType
    langfuse_endpoint: str | None
    langfuse_project_id: str | None
    contact_info: dict[str, Any] | None
    kpi_targets: dict[str, Any] | None
    created_at: Any
    updated_at: Any
