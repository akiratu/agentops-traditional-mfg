from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.anomaly_signal import (
    AnomalySignal,
    AnomalySignalCreate,
    AnomalySignalRead,
)

router = APIRouter(prefix="/anomaly-signals", tags=["anomaly_signal"])


@router.post("", response_model=AnomalySignalRead, status_code=status.HTTP_201_CREATED)
def create_signal(
    payload: AnomalySignalCreate, session: Session = Depends(get_session)
) -> AnomalySignal:
    signal = AnomalySignal(**payload.model_dump())
    session.add(signal)
    session.commit()
    session.refresh(signal)
    return signal


@router.get("", response_model=list[AnomalySignalRead])
def list_signals(
    agent_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> list[AnomalySignal]:
    stmt = select(AnomalySignal)
    if agent_id is not None:
        stmt = stmt.where(AnomalySignal.agent_id == agent_id)
    return list(session.exec(stmt).all())


@router.get("/{signal_id}", response_model=AnomalySignalRead)
def get_signal(
    signal_id: UUID, session: Session = Depends(get_session)
) -> AnomalySignal:
    signal = session.get(AnomalySignal, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Anomaly signal not found")
    return signal
