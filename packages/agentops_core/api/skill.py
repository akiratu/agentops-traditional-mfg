from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.agent import Agent
from agentops_core.models.skill import (
    Skill,
    SkillCreate,
    SkillRead,
    SkillStatus,
    SkillStatusUpdate,
)

router = APIRouter(prefix="/skills", tags=["skill"])


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: SkillCreate, session: Session = Depends(get_session)
) -> Skill:
    skill = Skill(**payload.model_dump())
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return skill


@router.get("", response_model=list[SkillRead])
def list_skills(
    agent_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> list[Skill]:
    stmt = select(Skill)
    if agent_id is not None:
        stmt = stmt.where(Skill.agent_id == agent_id)
    return list(session.exec(stmt).all())


@router.get("/{skill_id}", response_model=SkillRead)
def get_skill(skill_id: UUID, session: Session = Depends(get_session)) -> Skill:
    skill = session.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/{skill_id}/status", response_model=SkillRead)
def update_skill_status(
    skill_id: UUID,
    payload: SkillStatusUpdate,
    session: Session = Depends(get_session),
) -> Skill:
    skill = session.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    # If promoting to ACTIVE, demote any other ACTIVE skill on the same agent
    # to ARCHIVED and update the agent's current_skill_id pointer. Enforces
    # "exactly one active skill per agent" at the business-logic layer and
    # keeps the runtime pointer in sync with the active version.
    if payload.status == SkillStatus.ACTIVE:
        others = session.exec(
            select(Skill).where(
                Skill.agent_id == skill.agent_id,
                Skill.id != skill.id,
                Skill.status == SkillStatus.ACTIVE,
            )
        ).all()
        for other in others:
            other.status = SkillStatus.ARCHIVED
            session.add(other)
        agent = session.get(Agent, skill.agent_id)
        if agent is not None:
            agent.current_skill_id = skill.id
            session.add(agent)

    skill.status = payload.status
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return skill
