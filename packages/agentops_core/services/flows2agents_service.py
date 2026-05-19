"""Wrap flows2agents library entry points as in-process service calls.

This module is intentionally thin — it does NOT add domain logic.
It only adapts our DB rows (Agent, SOPSource) to flows2agents inputs,
calls the library, and returns the SkillIR for downstream mapping.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from flows2agents.evolve.models import EvolutionReport, FailureCase, RegressionReport
from flows2agents.evolve.pipeline import evolve_skill as f2a_evolve_skill
from flows2agents.ir import RawSource, SkillIR
from flows2agents.llm.base import LLMProvider
from flows2agents.pipeline import PipelineInputs, PipelineResult, run as f2a_run
from flows2agents.portfolio.builder import BuildOptions
from flows2agents.portfolio.builder import build_portfolio as f2a_build_portfolio
from flows2agents.portfolio.decomposer import decompose as f2a_decompose

from agentops_core.models.agent import Agent
from agentops_core.models.skill import Skill
from agentops_core.models.sop_source import SOPSource
from agentops_core.services.storage import LocalStorage


def generate_single_skill(
    *,
    agent: Agent,
    sop_sources: Sequence[SOPSource],
    storage: LocalStorage,
    provider: LLMProvider,
    strategy: str = "single",
) -> tuple[SkillIR, PipelineResult, str]:
    """Run flows2agents on the given SOPSources for the given Agent.

    Returns:
        (skill_ir, pipeline_result, generated_by_run_id) where:
        - skill_ir is the flows2agents IR (consumed by skill_mapper)
        - pipeline_result is the full PipelineResult (eval_report, skill_dir, ...)
        - generated_by_run_id is the RELATIVE PATH (from storage.root) to the
          actual skill_dir, e.g. "skills/f2a-abc123/yield-drop-rca". We store
          the path rather than a bare uuid because flows2agents nests the output
          as `<out_dir>/<skill_name>/` and Self-Evolve needs to find the exact
          subdir later. The path doubles as a unique run identifier and starts
          with "f2a-" via the run_bucket so it's easy to recognise.
    """
    run_bucket = f"f2a-{uuid4().hex[:12]}"
    out_dir = storage.dir_for(f"skills/{run_bucket}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)

    # flows2agents.load_docs reads files from disk paths.
    doc_paths: list[Path] = [storage.resolve(s.storage_ref) for s in sop_sources]
    inputs = PipelineInputs(description=agent.purpose, doc_paths=doc_paths)

    try:
        result = f2a_run(
            inputs,
            provider=provider,
            targets=["claude-skill"],
            out_dir=out_dir,
            force=True,
            enrich=provider.is_available(),
            strategy=strategy,
        )
    except Exception:
        # Cleanup partial output dir so subsequent runs don't trip on file conflicts.
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
        raise

    # result.skill_dir is e.g. <storage.root>/skills/f2a-abc123/yield-drop-rca
    # Record it as a relative path so Self-Evolve can resolve it later.
    skill_dir_relative = str(result.skill_dir.relative_to(storage.root))
    skill_ir = SkillIR.model_validate_json(result.ir_path.read_text(encoding="utf-8"))
    return skill_ir, result, skill_dir_relative


def generate_portfolio(
    *,
    factory_description: str,
    sop_sources: Sequence[SOPSource],
    storage: LocalStorage,
    provider: LLMProvider,
) -> dict:
    """Run flows2agents portfolio mode.

    Returns a dict with shape:
    {
      "run_id": "f2a-portfolio-<hex>",
      "plan": <PortfolioPlan as dict>,
      "built_skills": [
        {
          "agent_name": "...",
          "agent_display_name": "...",
          "skill_name": "...",
          "skill_ir": {...},
        },
        ...
      ],
    }

    The caller (API layer) is responsible for translating this into Agent + Skill DB rows.

    NOTE: decompose() takes list[RawSource] (not file paths). Each SOPSource's
    content is read from disk and wrapped as a RawSource(kind="doc").
    build_portfolio() returns a PortfolioIR; we unpack PortfolioIR.agents[].skills[].
    """
    run_id = f"f2a-portfolio-{uuid4().hex[:12]}"

    # Build RawSource list: one description from factory_description, plus one
    # "doc" RawSource per SOP file.
    raw_sources: list[RawSource] = [
        RawSource(kind="description", name="factory-description", text=factory_description),
    ]
    for sop in sop_sources:
        doc_path = storage.resolve(sop.storage_ref)
        text = doc_path.read_text(encoding="utf-8", errors="replace")
        raw_sources.append(RawSource(kind="doc", name=doc_path.stem, text=text))

    plan = f2a_decompose(
        sources=raw_sources,
        provider=provider,
    )

    portfolio_ir = f2a_build_portfolio(
        plan=plan,
        sources=raw_sources,
        provider=provider,
        options=BuildOptions(),
    )

    # Flatten PortfolioIR → list of per-skill dicts, keyed by agent info.
    built_skills = []
    for agent_ir in portfolio_ir.agents:
        for skill_ir in agent_ir.skills:
            built_skills.append(
                {
                    "agent_name": agent_ir.name,
                    "agent_display_name": agent_ir.display_name,
                    "agent_role": agent_ir.role,
                    "agent_scope": agent_ir.scope,
                    "skill_name": skill_ir.name,
                    "skill_ir": skill_ir.model_dump(),
                }
            )

    return {
        "run_id": run_id,
        "plan": plan.model_dump(),
        "built_skills": built_skills,
    }


def self_evolve_skill(
    *,
    skill: Skill,
    failures: Sequence[FailureCase],
    storage: LocalStorage,
    provider: LLMProvider,
) -> tuple[SkillIR, EvolutionReport, RegressionReport, str]:
    """Run flows2agents Self-Evolve on an existing skill with given failure cases.

    The caller must ensure `skill.generated_by_run_id` is set. By convention
    (see generate_single_skill) that value is a relative path from storage.root
    pointing at the previous skill_dir (e.g. "skills/f2a-abc/yield-drop-rca").

    Returns:
        (new_skill_ir, evolution_report, regression_report, new_skill_dir_relative)
        where new_skill_dir_relative is the relative path from storage.root to
        the new skill's directory (same convention as generate_single_skill).
    """
    if not skill.generated_by_run_id:
        raise ValueError(f"Skill {skill.id} has no generated_by_run_id; cannot evolve")

    old_skill_dir = storage.resolve(skill.generated_by_run_id)
    new_run_bucket = f"f2a-evolve-{uuid4().hex[:12]}"
    new_out_dir = storage.dir_for(f"skills/{new_run_bucket}")
    new_out_dir.parent.mkdir(parents=True, exist_ok=True)

    result = f2a_evolve_skill(
        skill_dir=old_skill_dir,
        failures=list(failures),
        provider=provider,
        out_dir=new_out_dir,
        targets=["claude-skill"],
        force=True,
        run_eval_after=True,
        run_regression_after=True,
    )
    new_skill_dir_relative = str(result.new_skill_dir.relative_to(storage.root))
    return result.new_ir, result.report, result.regression_report, new_skill_dir_relative
