from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlmodel import Session

from agentops_core.models.agent import Agent, RuntimeStatus
from agentops_core.models.anomaly_signal import (
    AnomalySignal,
    AnomalySourceType,
    AnomalyStatus,
)
from agentops_core.models.factory import Factory
from agentops_core.models.skill import Skill, SkillStatus
from agentops_core.services.anomaly_detector.orchestrator import (
    run_anomaly_check_all_agents,
    run_self_evolve_for_finding,
    run_trace_analyzer_for_signal,
)


def _seed_agent_with_skill(session: Session) -> tuple[Agent, Skill]:
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
    s = Skill(
        agent_id=a.id,
        version=1,
        status=SkillStatus.ACTIVE,
        prompt="v1",
        tool_specs=[],
        golden_test_cases=[],
        sop_source_set_id="s1",
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    a.current_skill_id = s.id
    session.add(a)
    session.commit()
    session.refresh(a)
    return a, s


def test_run_anomaly_check_iterates_only_running_agents(session):
    f = Factory(name="F1")
    session.add(f)
    session.commit()
    session.refresh(f)
    running = Agent(
        factory_id=f.id, name="run", purpose="p", runtime_status=RuntimeStatus.RUNNING
    )
    stopped = Agent(
        factory_id=f.id, name="stop", purpose="p", runtime_status=RuntimeStatus.STOPPED
    )
    session.add(running)
    session.add(stopped)
    session.commit()
    session.refresh(running)
    session.refresh(stopped)

    seen_agent_ids: list = []

    def fake_metric_drift(*, agent, session, langfuse_client, **kwargs):
        seen_agent_ids.append(agent.id)
        return None

    def fake_cost_spike(*, agent, session, langfuse_client, **kwargs):
        return None

    with (
        patch(
            "agentops_core.services.anomaly_detector.orchestrator.detect_metric_drift_for_agent",
            side_effect=fake_metric_drift,
        ),
        patch(
            "agentops_core.services.anomaly_detector.orchestrator.detect_cost_spike_for_agent",
            side_effect=fake_cost_spike,
        ),
    ):
        run_anomaly_check_all_agents(
            session_factory=lambda: session,
            langfuse_client_factory=lambda: MagicMock(),
        )

    assert running.id in seen_agent_ids
    assert stopped.id not in seen_agent_ids


def test_run_trace_analyzer_for_signal_calls_service(session):
    agent, _ = _seed_agent_with_skill(session)
    signal = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.METRIC_DRIFT,
        related_trace_refs=["t1"],
        status=AnomalyStatus.NEW,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)

    with patch(
        "agentops_core.services.anomaly_detector.orchestrator.analyze_anomaly_signal"
    ) as mock_analyze:
        mock_analyze.return_value = (MagicMock(id=uuid4()), [])
        run_trace_analyzer_for_signal(
            signal_id=signal.id,
            session_factory=lambda: session,
            langfuse_client_factory=lambda: MagicMock(),
        )
    mock_analyze.assert_called_once()


def test_run_self_evolve_for_finding_calls_service(session):
    agent, skill = _seed_agent_with_skill(session)
    signal = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.METRIC_DRIFT,
        related_trace_refs=[],
        status=AnomalyStatus.ANALYZING,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    from agentops_core.models.rca_finding import (
        RCAFinding,
        RCAFindingStatus,
        SuggestedFixType,
    )

    finding = RCAFinding(
        anomaly_signal_id=signal.id,
        root_cause_summary="x",
        evidence={},
        suggested_fix_type=SuggestedFixType.SUPPLEMENT_SOP,
        suggested_fix_payload={
            "failure_cases": [
                {
                    "id": "case-1",
                    "query": "q",
                    "expected_outcome": "e",
                    "actual_outcome": "a",
                    "context": None,
                }
            ]
        },
        confidence_score=0.85,
        status=RCAFindingStatus.ACCEPTED,
    )
    session.add(finding)
    session.commit()
    session.refresh(finding)

    with patch(
        "agentops_core.services.anomaly_detector.orchestrator.self_evolve_skill"
    ) as mock_evolve:
        mock_evolve.return_value = (
            MagicMock(),
            MagicMock(additive_violations=[]),
            MagicMock(total=1, results=[], notes=""),
            "skills/x/y",
        )
        run_self_evolve_for_finding(
            finding_id=finding.id,
            session_factory=lambda: session,
        )
    mock_evolve.assert_called_once()
