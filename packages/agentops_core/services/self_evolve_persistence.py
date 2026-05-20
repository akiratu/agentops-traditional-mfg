"""Shared persistence logic for the Self-Evolve flow.

Called from BOTH:
- ``api/self_evolve.py::create_self_evolution`` (synchronous HTTP endpoint)
- ``services/anomaly_detector/orchestrator.py::run_self_evolve_for_finding``
  (background task triggered by PATCH /rca-findings/{id}/status to ACCEPTED)

Before v0.3, the orchestrator path called ``self_evolve_skill`` directly
and only logged the result, silently failing to persist the new Skill /
RegressionRun rows to the DB. This module consolidates the persistence
so both paths behave identically.
"""

from __future__ import annotations

from collections.abc import Sequence

from flows2agents.llm.base import LLMProvider
from sqlmodel import Session, select

from agentops_core.models.regression_run import (
    RegressionRun,
    RegressionVerdict,
    TestSetStrategy,
)
from agentops_core.models.skill import Skill, SkillStatus
from agentops_core.schemas import FailureCase
from agentops_core.services.flows2agents_service import self_evolve_skill
from agentops_core.services.skill_mapper import skill_ir_to_skill_payload
from agentops_core.services.storage import LocalStorage


def persist_self_evolution(
    *,
    old_skill: Skill,
    failure_cases: Sequence[FailureCase],
    session: Session,
    storage: LocalStorage,
    provider: LLMProvider,
) -> tuple[Skill, RegressionRun]:
    """Run flows2agents Self-Evolve on ``old_skill`` and persist results.

    Returns (new_skill, regression_run) — both already saved to the DB and
    refreshed. The new skill is always created with ``status=DRAFT`` so a
    human reviewer (or the future auto-promote flow) must explicitly
    promote it via ``PATCH /skills/{id}/status``.

    Raises whatever ``self_evolve_skill`` raises (e.g. AnalyzerError when
    the LLM fails to produce structured output). Callers should catch
    and log.
    """
    new_ir, evolution_report, regression_report, new_run_id = self_evolve_skill(
        skill=old_skill,
        failures=list(failure_cases),
        storage=storage,
        provider=provider,
    )
    mapped = skill_ir_to_skill_payload(new_ir)

    # Determine next version for this agent.
    existing = list(
        session.exec(select(Skill).where(Skill.agent_id == old_skill.agent_id)).all()
    )
    next_version = max((s.version for s in existing), default=0) + 1

    new_skill = Skill(
        agent_id=old_skill.agent_id,
        version=next_version,
        status=SkillStatus.DRAFT,
        prompt=mapped["prompt"],
        tool_specs=mapped["tool_specs"],
        golden_test_cases=mapped["golden_test_cases"],
        sop_source_set_id=old_skill.sop_source_set_id,  # carry over
        generated_by_run_id=new_run_id,
    )
    session.add(new_skill)
    session.commit()
    session.refresh(new_skill)

    # Tally regression verdicts.
    pass_count = sum(1 for r in regression_report.results if r.verdict == "resolved")
    fail_count = sum(
        1 for r in regression_report.results if r.verdict == "still_broken"
    )
    review_count = sum(1 for r in regression_report.results if r.verdict == "partial")
    overall_verdict = (
        RegressionVerdict.PASS
        if fail_count == 0 and review_count == 0
        else (
            RegressionVerdict.NEEDS_REVIEW
            if fail_count == 0
            else RegressionVerdict.FAIL
        )
    )

    run = RegressionRun(
        skill_id_old=old_skill.id,
        skill_id_new=new_skill.id,
        test_set_strategy=TestSetStrategy.GOLDEN,
        test_case_count=regression_report.total,
        pass_count=pass_count,
        fail_count=fail_count,
        per_case_results=[r.model_dump() for r in regression_report.results],
        regression_findings=evolution_report.additive_violations,
        verdict=overall_verdict,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    return new_skill, run
