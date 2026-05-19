from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.regression_run import (
    RegressionRun,
    RegressionRunCreate,
    RegressionRunRead,
)

router = APIRouter(prefix="/regression-runs", tags=["regression_run"])


@router.post("", response_model=RegressionRunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RegressionRunCreate, session: Session = Depends(get_session)) -> RegressionRun:
    run = RegressionRun(**payload.model_dump())
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


@router.get("", response_model=list[RegressionRunRead])
def list_runs(
    skill_id_new: UUID | None = None,
    session: Session = Depends(get_session),
) -> list[RegressionRun]:
    stmt = select(RegressionRun)
    if skill_id_new is not None:
        stmt = stmt.where(RegressionRun.skill_id_new == skill_id_new)
    return list(session.exec(stmt).all())


@router.get("/{run_id}", response_model=RegressionRunRead)
def get_run(run_id: UUID, session: Session = Depends(get_session)) -> RegressionRun:
    run = session.get(RegressionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Regression run not found")
    return run
