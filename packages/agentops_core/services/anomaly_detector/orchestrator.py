"""Glue between scheduled detectors, signals, findings, and Self-Evolve.

Three entry points:

1. ``run_anomaly_check_all_agents()`` — called by APScheduler hourly.
   Iterates RUNNING agents, runs both detectors. Each detector may create
   an AnomalySignal; the API layer (anomaly_signal.py) is responsible for
   dispatching the trace analyzer via BackgroundTasks when a signal is
   created via the API. For scheduler-created signals, we dispatch from
   within this orchestrator using a fire-and-forget thread.

2. ``run_trace_analyzer_for_signal(signal_id)`` — called by FastAPI
   BackgroundTasks when a signal is POSTed (via /anomaly-signals or
   /human-flags) and by (1) above.

3. ``run_self_evolve_for_finding(finding_id)`` — called by FastAPI
   BackgroundTasks when a finding is PATCHed to ACCEPTED (Task 10).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from uuid import UUID

from sqlmodel import Session, select

from agentops_core.config import get_settings
from agentops_core.database import get_session, get_storage
from agentops_core.models.agent import Agent, RuntimeStatus
from agentops_core.models.anomaly_signal import AnomalySignal, AnomalyStatus
from agentops_core.models.rca_finding import RCAFinding, RCAFindingStatus
from agentops_core.schemas import FailureCase
from agentops_core.services.anomaly_detector.cost_spike import (
    detect_cost_spike_for_agent,
)
from agentops_core.services.anomaly_detector.metric_drift import (
    detect_metric_drift_for_agent,
)
from agentops_core.services.flows2agents_service import self_evolve_skill
from agentops_core.services.langfuse_client import LangfuseTraceClient
from agentops_core.services.trace_analyzer.service import analyze_anomaly_signal

log = logging.getLogger(__name__)


SessionFactory = Callable[[], Session]
LangfuseClientFactory = Callable[[], LangfuseTraceClient]


def _default_session_factory() -> Session:
    return next(get_session())


def _default_langfuse_client_factory() -> LangfuseTraceClient:
    return LangfuseTraceClient.from_settings(get_settings())


def run_anomaly_check_all_agents(
    *,
    session_factory: SessionFactory | None = None,
    langfuse_client_factory: LangfuseClientFactory | None = None,
) -> None:
    """For each RUNNING agent, run metric_drift + cost_spike detectors."""
    sf = session_factory or _default_session_factory
    lf_factory = langfuse_client_factory or _default_langfuse_client_factory

    session = sf()
    try:
        agents = list(
            session.exec(
                select(Agent).where(Agent.runtime_status == RuntimeStatus.RUNNING)
            ).all()
        )
    except Exception:
        log.exception("Failed to list RUNNING agents")
        return

    langfuse_client = lf_factory()
    for agent in agents:
        for fn in (detect_metric_drift_for_agent, detect_cost_spike_for_agent):
            try:
                signal = fn(
                    agent=agent,
                    session=session,
                    langfuse_client=langfuse_client,
                )
                if signal is not None:
                    threading.Thread(
                        target=run_trace_analyzer_for_signal,
                        kwargs={"signal_id": signal.id},
                        daemon=True,
                    ).start()
            except Exception:
                log.exception("Detector %s failed for agent %s", fn.__name__, agent.id)


def run_trace_analyzer_for_signal(
    *,
    signal_id: UUID,
    session_factory: SessionFactory | None = None,
    langfuse_client_factory: LangfuseClientFactory | None = None,
) -> None:
    """Dispatch the Trace Analyzer on one AnomalySignal."""
    sf = session_factory or _default_session_factory
    lf_factory = langfuse_client_factory or _default_langfuse_client_factory

    session = sf()
    signal = session.get(AnomalySignal, signal_id)
    if signal is None:
        log.warning("Signal %s not found; skip", signal_id)
        return

    signal.status = AnomalyStatus.ANALYZING
    session.add(signal)
    session.commit()

    try:
        finding, _failure_cases = analyze_anomaly_signal(
            anomaly_signal_id=signal_id,
            session=session,
            langfuse_client=lf_factory(),
            settings=get_settings(),
        )
        log.info(
            "Trace Analyzer produced finding %s for signal %s", finding.id, signal_id
        )
    except Exception:
        log.exception("Trace Analyzer failed for signal %s", signal_id)


def run_self_evolve_for_finding(
    *,
    finding_id: UUID,
    session_factory: SessionFactory | None = None,
) -> None:
    """When a finding is accepted, run Self-Evolve on its FailureCases."""
    sf = session_factory or _default_session_factory

    session = sf()
    finding = session.get(RCAFinding, finding_id)
    if finding is None:
        log.warning("Finding %s not found; skip", finding_id)
        return
    if finding.status != RCAFindingStatus.ACCEPTED:
        log.warning("Finding %s is %s, not accepted; skip", finding_id, finding.status)
        return

    raw_cases = finding.suggested_fix_payload.get("failure_cases", [])
    failure_cases = [FailureCase(**rc) for rc in raw_cases]
    if not failure_cases:
        log.warning("Finding %s has no failure_cases; skip", finding_id)
        return

    signal = session.get(AnomalySignal, finding.anomaly_signal_id)
    if signal is None:
        log.warning("Orphan finding %s; skip", finding_id)
        return
    agent = session.get(Agent, signal.agent_id)
    if agent is None or agent.current_skill_id is None:
        log.warning(
            "Agent missing or no current skill for finding %s; skip", finding_id
        )
        return

    from agentops_core.models.skill import Skill

    skill = session.get(Skill, agent.current_skill_id)
    if skill is None:
        log.warning("Skill %s not found; skip", agent.current_skill_id)
        return

    storage = get_storage()  # returns LocalStorage directly (not a generator)
    settings = get_settings()
    from agentops_core.services.llm_provider import build_provider

    provider = build_provider(settings)

    try:
        new_ir, evolution_report, regression_report, new_run_id = self_evolve_skill(
            skill=skill,
            failures=failure_cases,
            storage=storage,
            provider=provider,
        )
    except Exception:
        log.exception("Self-Evolve failed for finding %s", finding_id)
        return

    log.info(
        "Self-Evolve produced new skill run %s for finding %s (regression: %s)",
        new_run_id,
        finding_id,
        regression_report.notes,
    )
