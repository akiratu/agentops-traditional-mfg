from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.agent import (
    Agent,
    AgentCreate,
    AgentCurrentSkillUpdate,
    AgentRead,
    AgentRuntimeStatusUpdate,
    RuntimeStatus,
)
from agentops_core.models.skill import Skill

router = APIRouter(prefix="/agents", tags=["agent"])


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate, session: Session = Depends(get_session)
) -> Agent:
    agent = Agent(**payload.model_dump())
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("", response_model=list[AgentRead])
def list_agents(
    factory_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> list[Agent]:
    stmt = select(Agent)
    if factory_id is not None:
        stmt = stmt.where(Agent.factory_id == factory_id)
    return list(session.exec(stmt).all())


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: UUID, session: Session = Depends(get_session)) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}/current-skill", response_model=AgentRead)
def update_agent_current_skill(
    agent_id: UUID,
    payload: AgentCurrentSkillUpdate,
    session: Session = Depends(get_session),
) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if payload.current_skill_id is not None:
        skill = session.get(Skill, payload.current_skill_id)
        if skill is None:
            raise HTTPException(
                status_code=400, detail="Skill not found; cannot promote"
            )
        if skill.agent_id != agent.id:
            raise HTTPException(
                status_code=400,
                detail="Skill belongs to a different agent",
            )

    agent.current_skill_id = payload.current_skill_id
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.patch("/{agent_id}/runtime-status", response_model=AgentRead)
def update_agent_runtime_status(
    agent_id: UUID,
    payload: AgentRuntimeStatusUpdate,
    session: Session = Depends(get_session),
) -> Agent:
    from datetime import datetime

    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # First transition to RUNNING stamps deployed_at. Subsequent transitions
    # (stopped, error, deploying-again) leave it as a historical first-deploy
    # marker — operators can read it as "first went live at".
    if payload.runtime_status == RuntimeStatus.RUNNING and agent.deployed_at is None:
        agent.deployed_at = datetime.now(tz=UTC)

    agent.runtime_status = payload.runtime_status
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent
