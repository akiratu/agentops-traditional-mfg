"""Cost spike detector.

Compares the average cost-per-trace in the last 24h against the prior 7-day
mean. If the 24h mean exceeds `spike_multiplier` × baseline (default 1.5×),
creates an AnomalySignal.

Cost is read from `trace.metadata.cost_usd`. Traces without cost data are
ignored; if no usable traces exist, the detector silently skips.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session

from agentops_core.models.agent import Agent
from agentops_core.models.anomaly_signal import (
    AnomalySignal,
    AnomalySourceType,
    AnomalyStatus,
)
from agentops_core.services.anomaly_detector.metric_drift import _has_open_signal
from agentops_core.services.langfuse_client import LangfuseTraceClient

log = logging.getLogger(__name__)

BASELINE_DAYS = 7
RECENT_HOURS = 24
MIN_TRACES_PER_BUCKET = 3
COST_METADATA_KEY = "cost_usd"


def detect_cost_spike_for_agent(
    *,
    agent: Agent,
    session: Session,
    langfuse_client: LangfuseTraceClient,
    spike_multiplier: float = 1.5,
) -> AnomalySignal | None:
    """Detect cost spike for one agent; create signal if spike detected."""
    if _has_open_signal(session, agent_id=agent.id):
        return None

    now = datetime.now(tz=UTC)
    baseline_start = now - timedelta(days=BASELINE_DAYS)
    recent_start = now - timedelta(hours=RECENT_HOURS)

    try:
        traces = langfuse_client.search_traces(
            agent_id=str(agent.id),
            since=baseline_start,
            limit=500,
        )
    except RuntimeError as exc:
        log.warning("Langfuse unavailable for %s: %s", agent.id, exc)
        return None

    baseline, recent = _split_by_recent_window(traces, recent_start)
    if len(baseline) < MIN_TRACES_PER_BUCKET or len(recent) < MIN_TRACES_PER_BUCKET:
        return None

    baseline_mean = _mean_cost(baseline)
    recent_mean = _mean_cost(recent)
    if baseline_mean is None or recent_mean is None or baseline_mean <= 0:
        return None

    if recent_mean < baseline_mean * spike_multiplier:
        return None

    signal = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.COST_SPIKE,
        related_trace_refs=[t["id"] for t in recent[:10]],
        status=AnomalyStatus.NEW,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    log.info(
        "Cost spike on agent %s: baseline=$%.4f, recent=$%.4f (×%.2f) → signal %s",
        agent.id,
        baseline_mean,
        recent_mean,
        recent_mean / baseline_mean if baseline_mean else 0.0,
        signal.id,
    )
    return signal


def _split_by_recent_window(
    traces: list[dict[str, Any]],
    recent_start: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    rs = recent_start if recent_start.tzinfo else recent_start.replace(tzinfo=UTC)
    for t in traces:
        ts = _parse_iso(t.get("timestamp"))
        if ts is None:
            continue
        ts_aware = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
        (recent if ts_aware >= rs else baseline).append(t)
    return baseline, recent


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _mean_cost(traces: list[dict[str, Any]]) -> float | None:
    values = [t.get("metadata", {}).get(COST_METADATA_KEY) for t in traces]
    floats = [v for v in values if isinstance(v, (int, float))]
    if not floats:
        return None
    return sum(floats) / len(floats)
