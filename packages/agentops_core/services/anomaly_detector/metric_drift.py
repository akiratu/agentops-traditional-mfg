"""Metric drift detector.

Compares the mean of the `rca_accuracy` score over two consecutive 7-day
windows. If the recent window's mean dropped by more than `drop_threshold`
relative to the prior window's mean, creates an AnomalySignal with
source_type=metric_drift.

Insufficient data (fewer than 3 traces in either window) → no signal.
Open signals (NEW / ANALYZING) for the same agent → dedupe (no signal).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from agentops_core.models.agent import Agent
from agentops_core.models.anomaly_signal import (
    AnomalySignal,
    AnomalySourceType,
    AnomalyStatus,
)
from agentops_core.services.langfuse_client import LangfuseTraceClient

log = logging.getLogger(__name__)

WINDOW_DAYS = 7
MIN_TRACES_PER_WINDOW = 3
SCORE_NAME = "rca_accuracy"


def detect_metric_drift_for_agent(
    *,
    agent: Agent,
    session: Session,
    langfuse_client: LangfuseTraceClient,
    drop_threshold: float = 0.05,
) -> AnomalySignal | None:
    """Inspect this agent's last 14 days of traces; create signal if drift detected."""
    if _has_open_signal(session, agent_id=agent.id):
        log.debug("Skipping %s: open signal exists", agent.id)
        return None

    now = datetime.now(tz=UTC)
    window_a_start = now - timedelta(days=WINDOW_DAYS * 2)
    boundary = now - timedelta(days=WINDOW_DAYS)

    try:
        traces = langfuse_client.search_traces(
            agent_id=str(agent.id),
            since=window_a_start,
            limit=500,
        )
    except RuntimeError as exc:
        log.warning("Langfuse unavailable for %s: %s", agent.id, exc)
        return None

    prior, recent = _split_by_window(traces, boundary)
    if len(prior) < MIN_TRACES_PER_WINDOW or len(recent) < MIN_TRACES_PER_WINDOW:
        return None

    prior_mean = _mean_score(prior)
    recent_mean = _mean_score(recent)
    if prior_mean is None or recent_mean is None:
        return None

    drop = prior_mean - recent_mean
    if drop <= drop_threshold:
        return None

    failed_trace_refs = [t["id"] for t in recent if _trace_failed(t)][:10]

    signal = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.METRIC_DRIFT,
        related_trace_refs=failed_trace_refs,
        status=AnomalyStatus.NEW,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    log.info(
        "Metric drift on agent %s: prior=%.2f, recent=%.2f, drop=%.2f → signal %s",
        agent.id,
        prior_mean,
        recent_mean,
        drop,
        signal.id,
    )
    return signal


def _has_open_signal(session: Session, *, agent_id: Any) -> bool:
    open_statuses = (AnomalyStatus.NEW, AnomalyStatus.ANALYZING)
    rows = session.exec(
        select(AnomalySignal).where(
            AnomalySignal.agent_id == agent_id,
            AnomalySignal.status.in_(open_statuses),
        )
    ).all()
    return len(rows) > 0


def _split_by_window(
    traces: list[dict[str, Any]],
    boundary: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prior: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    for t in traces:
        ts = _parse_iso(t.get("timestamp"))
        if ts is None:
            continue
        b = boundary if boundary.tzinfo else boundary.replace(tzinfo=UTC)
        ts_aware = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
        (recent if ts_aware >= b else prior).append(t)
    return prior, recent


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _mean_score(traces: list[dict[str, Any]]) -> float | None:
    values = [
        s.get("value")
        for t in traces
        for s in (t.get("scores") or [])
        if s.get("name") == SCORE_NAME and isinstance(s.get("value"), (int, float))
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _trace_failed(trace: dict[str, Any]) -> bool:
    for s in trace.get("scores") or []:
        v = s.get("value")
        if isinstance(v, (int, float)) and v < 0.5:
            return True
    return False
