from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from sqlmodel import Session

from agentops_core.models.agent import Agent, RuntimeStatus
from agentops_core.models.anomaly_signal import AnomalySourceType
from agentops_core.models.factory import Factory
from agentops_core.services.anomaly_detector.cost_spike import (
    detect_cost_spike_for_agent,
)


def _seed_agent(session: Session) -> Agent:
    f = Factory(name="F1")
    session.add(f)
    session.commit()
    session.refresh(f)
    a = Agent(
        factory_id=f.id, name="A1", purpose="p",
        runtime_status=RuntimeStatus.RUNNING,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _trace_with_cost(cost: float, hours_ago: float) -> dict:
    return {
        "id": f"trace_cost_{cost}_{hours_ago}",
        "name": "rca",
        "timestamp": (
            datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
        ).isoformat(),
        "metadata": {"cost_usd": cost},
        "scores": [],
    }


def test_cost_spike_fires_when_24h_doubles_baseline(session: Session):
    """7d baseline ~ $0.10/trace, last 24h ~ $0.50/trace → 5x spike."""
    agent = _seed_agent(session)
    fake_lf = MagicMock()
    fake_lf.search_traces.return_value = (
        [_trace_with_cost(0.10, 30), _trace_with_cost(0.12, 50), _trace_with_cost(0.08, 100)]
        + [_trace_with_cost(0.50, 5), _trace_with_cost(0.60, 12), _trace_with_cost(0.40, 20)]
    )
    signal = detect_cost_spike_for_agent(
        agent=agent, session=session, langfuse_client=fake_lf,
        spike_multiplier=1.5,
    )
    assert signal is not None
    assert signal.source_type == AnomalySourceType.COST_SPIKE


def test_cost_spike_no_signal_when_stable(session: Session):
    agent = _seed_agent(session)
    fake_lf = MagicMock()
    fake_lf.search_traces.return_value = (
        [_trace_with_cost(0.10, 30), _trace_with_cost(0.12, 50), _trace_with_cost(0.10, 100)]
        + [_trace_with_cost(0.11, 5), _trace_with_cost(0.10, 12), _trace_with_cost(0.13, 20)]
    )
    signal = detect_cost_spike_for_agent(
        agent=agent, session=session, langfuse_client=fake_lf,
        spike_multiplier=1.5,
    )
    assert signal is None


def test_cost_spike_skips_when_no_cost_metadata(session: Session):
    agent = _seed_agent(session)
    fake_lf = MagicMock()
    fake_lf.search_traces.return_value = [
        {
            "id": "t1", "name": "rca",
            "timestamp": (datetime.now(tz=timezone.utc) - timedelta(hours=5)).isoformat(),
            "metadata": {},
            "scores": [],
        }
    ]
    signal = detect_cost_spike_for_agent(
        agent=agent, session=session, langfuse_client=fake_lf,
        spike_multiplier=1.5,
    )
    assert signal is None
