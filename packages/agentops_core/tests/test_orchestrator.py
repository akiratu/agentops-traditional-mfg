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
        "agentops_core.services.anomaly_detector.orchestrator.persist_self_evolution"
    ) as mock_persist:
        mock_persist.return_value = (MagicMock(id=uuid4()), MagicMock(id=uuid4()))
        run_self_evolve_for_finding(
            finding_id=finding.id,
            session_factory=lambda: session,
        )
    mock_persist.assert_called_once()


def test_run_self_evolve_for_finding_persists_skill_and_regression_run(session):
    """v0.3 fix: orchestrator must actually write Skill + RegressionRun rows."""
    from sqlmodel import select

    from agentops_core.models.rca_finding import (
        RCAFinding,
        RCAFindingStatus,
        SuggestedFixType,
    )
    from agentops_core.models.regression_run import RegressionRun

    agent, skill_v1 = _seed_agent_with_skill(session)
    signal = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.METRIC_DRIFT,
        related_trace_refs=[],
        status=AnomalyStatus.ANALYZING,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
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

    # Mock the flows2agents call (the LLM-driving function) but NOT persistence.
    # The orchestrator should still produce a Skill row + RegressionRun row.
    fake_ir = MagicMock()
    fake_ir.model_dump.return_value = {}
    with (
        patch(
            "agentops_core.services.self_evolve_persistence.self_evolve_skill"
        ) as mock_evolve,
        patch(
            "agentops_core.services.self_evolve_persistence.skill_ir_to_skill_payload"
        ) as mock_mapper,
    ):
        mock_evolve.return_value = (
            fake_ir,
            MagicMock(additive_violations=[]),
            MagicMock(total=1, results=[], notes=""),
            "skills/f2a-evolve-fake/cnc",
        )
        mock_mapper.return_value = {
            "prompt": "v2 prompt",
            "tool_specs": [],
            "golden_test_cases": [],
        }
        run_self_evolve_for_finding(
            finding_id=finding.id,
            session_factory=lambda: session,
        )

    # Verify persistence
    all_skills = list(
        session.exec(select(Skill).where(Skill.agent_id == agent.id)).all()
    )
    assert len(all_skills) == 2, "should have v1 + new v2 skill"
    new_skill = next(s for s in all_skills if s.id != skill_v1.id)
    assert new_skill.version == 2
    assert new_skill.status == SkillStatus.DRAFT
    assert new_skill.generated_by_run_id == "skills/f2a-evolve-fake/cnc"

    runs = list(
        session.exec(
            select(RegressionRun).where(RegressionRun.skill_id_new == new_skill.id)
        ).all()
    )
    assert len(runs) == 1
    assert runs[0].skill_id_old == skill_v1.id
