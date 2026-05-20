"""POST /human-flags — factory-mode users flag a trace as wrong.

Creates an AnomalySignal with source_type=human_flag pointing at the
specified trace. The orchestrator (Plan 4 Task 11) picks up new signals
and dispatches the Trace Analyzer.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from agentops_core.database import get_session
from agentops_core.models.agent import Agent
from agentops_core.models.anomaly_signal import (
    AnomalySignal,
    AnomalySignalRead,
    AnomalySourceType,
    AnomalyStatus,
)
from agentops_core.services.anomaly_detector.orchestrator import (
    run_trace_analyzer_for_signal,
)

router = APIRouter(prefix="/human-flags", tags=["human_flag"])


class HumanFlagRequest(BaseModel):
    agent_id: UUID
    trace_id: str
    comment: str | None = None


@router.post("", response_model=AnomalySignalRead, status_code=status.HTTP_201_CREATED)
def create_human_flag(
    payload: HumanFlagRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> AnomalySignal:
    agent = session.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    signal = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.HUMAN_FLAG,
        related_trace_refs=[payload.trace_id],
        status=AnomalyStatus.NEW,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    background_tasks.add_task(run_trace_analyzer_for_signal, signal_id=signal.id)
    return signal
