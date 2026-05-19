"""POST /skill-generations — orchestrates flows2agents single-skill generation."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from flows2agents.llm.base import LLMProvider
from pydantic import BaseModel
from sqlmodel import Session, select

from agentops_core.database import get_provider, get_session, get_storage
from agentops_core.models.agent import Agent
from agentops_core.models.skill import Skill, SkillRead, SkillStatus
from agentops_core.models.sop_source import SOPSource
from agentops_core.services.flows2agents_service import generate_single_skill
from agentops_core.services.skill_mapper import skill_ir_to_skill_payload
from agentops_core.services.storage import LocalStorage

router = APIRouter(prefix="/skill-generations", tags=["skill_generation"])


class SkillGenerationRequest(BaseModel):
    agent_id: UUID
    sop_source_ids: list[UUID]
    sop_source_set_id: str | None = None
    strategy: str = "single"


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill_generation(
    payload: SkillGenerationRequest,
    session: Session = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
    provider: LLMProvider = Depends(get_provider),
) -> Skill:
    agent = session.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not payload.sop_source_ids:
        raise HTTPException(status_code=400, detail="At least one sop_source_id required")

    sops = list(
        session.exec(select(SOPSource).where(SOPSource.id.in_(payload.sop_source_ids))).all()
    )
    if len(sops) != len(payload.sop_source_ids):
        raise HTTPException(status_code=404, detail="One or more SOP sources not found")

    skill_ir, _result, run_id = generate_single_skill(
        agent=agent,
        sop_sources=sops,
        storage=storage,
        provider=provider,
        strategy=payload.strategy,
    )
    payload_dict = skill_ir_to_skill_payload(skill_ir)

    # Compute next version for this agent
    existing = list(session.exec(select(Skill).where(Skill.agent_id == agent.id)).all())
    next_version = max((s.version for s in existing), default=0) + 1

    sop_set_id = payload.sop_source_set_id or f"set-{run_id}"
    skill = Skill(
        agent_id=agent.id,
        version=next_version,
        status=SkillStatus.DRAFT,
        prompt=payload_dict["prompt"],
        tool_specs=payload_dict["tool_specs"],
        golden_test_cases=payload_dict["golden_test_cases"],
        sop_source_set_id=sop_set_id,
        generated_by_run_id=run_id,
    )
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return skill
