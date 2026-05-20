"""Internal helpers shared by anomaly detectors."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from agentops_core.models.anomaly_signal import AnomalySignal, AnomalyStatus


def has_open_signal(session: Session, *, agent_id: Any) -> bool:
    """Return True if there's an OPEN (NEW or ANALYZING) signal for this agent."""
    open_statuses = (AnomalyStatus.NEW, AnomalyStatus.ANALYZING)
    rows = session.exec(
        select(AnomalySignal).where(
            AnomalySignal.agent_id == agent_id,
            AnomalySignal.status.in_(open_statuses),
        )
    ).all()
    return len(rows) > 0
