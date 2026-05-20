"""POST /self-evolutions — flows2agents Self-Evolve + Skill v_next + RegressionRun.

Thin endpoint: delegates the actual orchestration to
``services.self_evolve_persistence.persist_self_evolution`` so the
background-task path (orchestrator) and the synchronous-HTTP path stay
in sync.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from flows2agents.llm.base import LLMProvider
from pydantic import BaseModel
from sqlmodel import Session

from agentops_core.database import get_provider, get_session, get_storage
from agentops_core.models.regression_run import RegressionRunRead
from agentops_core.models.skill import Skill, SkillRead
from agentops_core.schemas import FailureCase
from agentops_core.services.self_evolve_persistence import persist_self_evolution
from agentops_core.services.storage import LocalStorage

router = APIRouter(prefix="/self-evolutions", tags=["self_evolve"])


class SelfEvolveRequest(BaseModel):
    skill_id: UUID
    failure_cases: list[FailureCase]


class SelfEvolveResponse(BaseModel):
    skill: SkillRead
    regression_run: RegressionRunRead


@router.post("", response_model=SelfEvolveResponse, status_code=status.HTTP_201_CREATED)
def create_self_evolution(
    payload: SelfEvolveRequest,
    session: Session = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
    provider: LLMProvider = Depends(get_provider),
) -> SelfEvolveResponse:
    old_skill = session.get(Skill, payload.skill_id)
    if old_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    if not payload.failure_cases:
        raise HTTPException(
            status_code=400, detail="At least one failure case required"
        )

    new_skill, run = persist_self_evolution(
        old_skill=old_skill,
        failure_cases=payload.failure_cases,
        session=session,
        storage=storage,
        provider=provider,
    )

    # Use from_attributes=True so Pydantic reads fields off the SQLModel row
    # directly instead of via .model_dump() (which can return {} when the
    # session state isn't fully attribute-loaded after refresh).
    return SelfEvolveResponse(
        skill=SkillRead.model_validate(new_skill, from_attributes=True),
        regression_run=RegressionRunRead.model_validate(run, from_attributes=True),
    )
