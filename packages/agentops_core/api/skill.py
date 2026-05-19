from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.skill import Skill, SkillCreate, SkillRead

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
