from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from sqlmodel import Session, select

from agentops_core.models.agent import Agent, RuntimeStatus
from agentops_core.models.anomaly_signal import (
    AnomalySignal,
    AnomalySourceType,
)
from agentops_core.models.factory import Factory
from agentops_core.services.anomaly_detector.metric_drift import (
    detect_metric_drift_for_agent,
)


def _seed_agent(session: Session) -> Agent:
    f = Factory(name="F1")
    session.add(f)
    session.commit()
    session.refresh(f)
    a = Agent(
        factory_id=f.id,
        name="A1",
        purpose="p",
        runtime_status=RuntimeStatus.RUNNING,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _trace_summary(score_value: float, days_ago: float) -> dict:
    return {
        "id": f"trace_{score_value}_{days_ago}",
        "name": "rca",
        "timestamp": (datetime.now(tz=UTC) - timedelta(days=days_ago)).isoformat(),
        "metadata": {},
        "scores": [{"name": "rca_accuracy", "value": score_value}],
    }


def test_metric_drift_creates_signal_on_drop(session: Session):
    """Prior 7d mean = 0.9, recent 7d mean = 0.5 → drop > 5pp → fire."""
    agent = _seed_agent(session)
    fake_lf = MagicMock()
    fake_lf.search_traces.return_value = (
        # Prior window (8-14 days ago): high accuracy
        [_trace_summary(1.0, 8.5), _trace_summary(0.9, 10.0), _trace_summary(0.8, 12.0)]
        # Recent window (0-7 days ago): low accuracy
        + [_trace_summary(0.0, 1.0), _trace_summary(0.5, 3.0), _trace_summary(0.5, 5.0)]
    )

    signal = detect_metric_drift_for_agent(
        agent=agent,
        session=session,
        langfuse_client=fake_lf,
        drop_threshold=0.05,
    )
    assert signal is not None
    assert signal.source_type == AnomalySourceType.METRIC_DRIFT
    assert signal.agent_id == agent.id


def test_metric_drift_no_signal_when_stable(session: Session):
    """Both windows around 0.9 → no signal."""
    agent = _seed_agent(session)
    fake_lf = MagicMock()
    fake_lf.search_traces.return_value = [
        _trace_summary(1.0, 8.0),
        _trace_summary(0.9, 11.0),
    ] + [_trace_summary(0.9, 2.0), _trace_summary(1.0, 4.0)]

    signal = detect_metric_drift_for_agent(
        agent=agent,
        session=session,
        langfuse_client=fake_lf,
        drop_threshold=0.05,
    )
    assert signal is None


def test_metric_drift_skips_when_insufficient_data(session: Session):
    """Fewer than 3 traces in either window → skip (not enough signal)."""
    agent = _seed_agent(session)
    fake_lf = MagicMock()
    fake_lf.search_traces.return_value = [_trace_summary(0.0, 1.0)]

    signal = detect_metric_drift_for_agent(
        agent=agent,
        session=session,
        langfuse_client=fake_lf,
        drop_threshold=0.05,
    )
    assert signal is None


def test_metric_drift_dedupe_does_not_create_duplicate(session: Session):
    """If a NEW signal exists for the agent, skip — don't pile on."""
    agent = _seed_agent(session)
    existing = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.METRIC_DRIFT,
        related_trace_refs=[],
        status="new",
    )
    session.add(existing)
    session.commit()

    fake_lf = MagicMock()
    fake_lf.search_traces.return_value = [
        _trace_summary(1.0, 8.0),
        _trace_summary(0.9, 11.0),
        _trace_summary(0.8, 13.0),
    ] + [_trace_summary(0.0, 1.0), _trace_summary(0.0, 3.0), _trace_summary(0.5, 5.0)]
    signal = detect_metric_drift_for_agent(
        agent=agent,
        session=session,
        langfuse_client=fake_lf,
        drop_threshold=0.05,
    )
    assert signal is None
    rows = list(session.exec(select(AnomalySignal)).all())
    assert len(rows) == 1
