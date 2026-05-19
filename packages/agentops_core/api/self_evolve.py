"""POST /self-evolutions — flows2agents Self-Evolve + Skill v_next + RegressionRun."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from flows2agents.llm.base import LLMProvider
from pydantic import BaseModel
from sqlmodel import Session, select

from agentops_core.database import get_provider, get_session, get_storage
from agentops_core.models.regression_run import (
    RegressionRun,
    RegressionRunRead,
    RegressionVerdict,
    TestSetStrategy,
)
from agentops_core.models.skill import Skill, SkillRead, SkillStatus
from agentops_core.schemas import FailureCase
from agentops_core.services.flows2agents_service import self_evolve_skill
from agentops_core.services.skill_mapper import skill_ir_to_skill_payload
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
        raise HTTPException(status_code=400, detail="At least one failure case required")

    new_ir, evolution_report, regression_report, new_run_id = self_evolve_skill(
        skill=old_skill,
        failures=payload.failure_cases,
        storage=storage,
        provider=provider,
    )
    mapped = skill_ir_to_skill_payload(new_ir)

    # Determine next version for this agent
    existing = list(
        session.exec(select(Skill).where(Skill.agent_id == old_skill.agent_id)).all()
    )
    next_version = max((s.version for s in existing), default=0) + 1

    new_skill = Skill(
        agent_id=old_skill.agent_id,
        version=next_version,
        status=SkillStatus.DRAFT,
        prompt=mapped["prompt"],
        tool_specs=mapped["tool_specs"],
        golden_test_cases=mapped["golden_test_cases"],
        sop_source_set_id=old_skill.sop_source_set_id,  # carry over
        generated_by_run_id=new_run_id,
    )
    session.add(new_skill)
    session.commit()
    session.refresh(new_skill)

    # Tally regression results
    pass_count = sum(1 for r in regression_report.results if r.verdict == "resolved")
    fail_count = sum(1 for r in regression_report.results if r.verdict == "still_broken")
    review_count = sum(1 for r in regression_report.results if r.verdict == "partial")
    overall_verdict = (
        RegressionVerdict.PASS
        if fail_count == 0 and review_count == 0
        else RegressionVerdict.NEEDS_REVIEW
        if fail_count == 0
        else RegressionVerdict.FAIL
    )

    run = RegressionRun(
        skill_id_old=old_skill.id,
        skill_id_new=new_skill.id,
        test_set_strategy=TestSetStrategy.GOLDEN,
        test_case_count=regression_report.total,
        pass_count=pass_count,
        fail_count=fail_count,
        per_case_results=[r.model_dump() for r in regression_report.results],
        regression_findings=evolution_report.additive_violations,
        verdict=overall_verdict,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    return SelfEvolveResponse(
        skill=SkillRead.model_validate(new_skill.model_dump()),
        regression_run=RegressionRunRead.model_validate(run.model_dump()),
    )
