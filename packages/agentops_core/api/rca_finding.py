"""RCA Finding endpoints — list, create, get, status patch with side-effects."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from agentops_core.database import get_session
from agentops_core.models.rca_finding import (
    RCAFinding,
    RCAFindingCreate,
    RCAFindingRead,
    RCAFindingStatus,
    RCAFindingStatusUpdate,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/rca-findings", tags=["rca_finding"])


@router.post("", response_model=RCAFindingRead, status_code=status.HTTP_201_CREATED)
def create_finding(
    payload: RCAFindingCreate, session: Session = Depends(get_session)
) -> RCAFinding:
    finding = RCAFinding(**payload.model_dump())
    session.add(finding)
    session.commit()
    session.refresh(finding)
    return finding


@router.get("", response_model=list[RCAFindingRead])
def list_findings(
    anomaly_signal_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> list[RCAFinding]:
    stmt = select(RCAFinding)
    if anomaly_signal_id is not None:
        stmt = stmt.where(RCAFinding.anomaly_signal_id == anomaly_signal_id)
    return list(session.exec(stmt).all())


@router.get("/{finding_id}", response_model=RCAFindingRead)
def get_finding(
    finding_id: UUID, session: Session = Depends(get_session)
) -> RCAFinding:
    finding = session.get(RCAFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="RCA finding not found")
    return finding


def dispatch_self_evolve_background(*, finding_id: UUID) -> None:
    """Background task: fire Self-Evolve on the failure_cases attached to a finding.

    Implementation lives in services/anomaly_detector/orchestrator.py (Task 11).
    The hook is patched in tests so the body is irrelevant to test outcomes.
    """
    from agentops_core.services.anomaly_detector.orchestrator import (
        run_self_evolve_for_finding,
    )

    try:
        run_self_evolve_for_finding(finding_id=finding_id)
    except Exception:
        log.exception("Self-Evolve background task failed for finding %s", finding_id)


@router.patch("/{finding_id}/status", response_model=RCAFindingRead)
def update_finding_status(
    finding_id: UUID,
    payload: RCAFindingStatusUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> RCAFinding:
    finding = session.get(RCAFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="RCA finding not found")
    finding.status = payload.status
    session.add(finding)
    session.commit()
    session.refresh(finding)

    if payload.status == RCAFindingStatus.ACCEPTED:
        background_tasks.add_task(
            dispatch_self_evolve_background, finding_id=finding.id
        )

    return finding
