from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.agent import Agent, AgentCreate, AgentRead

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
