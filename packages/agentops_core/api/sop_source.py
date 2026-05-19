from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.sop_source import (
    SOPSource,
    SOPSourceCreate,
    SOPSourceRead,
)

router = APIRouter(prefix="/sop-sources", tags=["sop_source"])


@router.post("", response_model=SOPSourceRead, status_code=status.HTTP_201_CREATED)
def create_sop_source(
    payload: SOPSourceCreate, session: Session = Depends(get_session)
) -> SOPSourceRead:
    data = payload.model_dump()
    metadata = data.pop("metadata", {})
    sop = SOPSource(**data, metadata_=metadata)
    session.add(sop)
    session.commit()
    session.refresh(sop)
    return SOPSourceRead.model_validate_sop(sop)


@router.get("", response_model=list[SOPSourceRead])
def list_sop_sources(
    factory_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> list[SOPSourceRead]:
    stmt = select(SOPSource)
    if factory_id is not None:
        stmt = stmt.where(SOPSource.factory_id == factory_id)
    return [SOPSourceRead.model_validate_sop(s) for s in session.exec(stmt).all()]


@router.get("/{sop_id}", response_model=SOPSourceRead)
def get_sop_source(
    sop_id: UUID, session: Session = Depends(get_session)
) -> SOPSourceRead:
    sop = session.get(SOPSource, sop_id)
    if sop is None:
        raise HTTPException(status_code=404, detail="SOP source not found")
    return SOPSourceRead.model_validate_sop(sop)
