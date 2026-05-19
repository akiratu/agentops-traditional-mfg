from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.factory import Factory, FactoryCreate, FactoryRead

router = APIRouter(prefix="/factories", tags=["factory"])


@router.post("", response_model=FactoryRead, status_code=status.HTTP_201_CREATED)
def create_factory(payload: FactoryCreate, session: Session = Depends(get_session)) -> Factory:
    factory = Factory(**payload.model_dump())
    session.add(factory)
    session.commit()
    session.refresh(factory)
    return factory


@router.get("", response_model=list[FactoryRead])
def list_factories(session: Session = Depends(get_session)) -> list[Factory]:
    return list(session.exec(select(Factory)).all())


@router.get("/{factory_id}", response_model=FactoryRead)
def get_factory(factory_id: UUID, session: Session = Depends(get_session)) -> Factory:
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise HTTPException(status_code=404, detail="Factory not found")
    return factory
