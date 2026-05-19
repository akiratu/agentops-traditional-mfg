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

from flows2agents.ir import SkillIR
from flows2agents.llm.base import LLMProvider
from flows2agents.pipeline import PipelineInputs, PipelineResult, run as f2a_run

from agentops_core.models.agent import Agent
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
