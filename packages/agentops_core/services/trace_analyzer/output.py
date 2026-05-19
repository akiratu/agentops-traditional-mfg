"""Translate TraceAnalyzerOutput into an RCAFindingCreate payload."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from agentops_core.models.rca_finding import RCAFindingStatus, SuggestedFixType
from agentops_core.services.trace_analyzer.agent import TraceAnalyzerOutput


def build_rca_finding_payload(
    output: TraceAnalyzerOutput,
    *,
    anomaly_signal_id: UUID,
) -> dict[str, Any]:
    """Return a dict suitable for RCAFindingCreate.model_validate(...).

    Heuristics:
    - root_cause_summary: derived from the first FailureCase's expected_outcome
      (which by spec describes what the skill SHOULD have done — i.e., the gap).
    - suggested_fix_type: 'supplement_sop' is the safe default for v0.1
      (most failures resolve by adding to the SOP corpus). v0.2 can use the
      LLM to classify into prompt_change / add_skill / swap_model / etc.
    - confidence_score: 0.85 max if normal termination, 0.2 if no-evidence fallback.
    """
    fcs = output.failure_cases
    is_no_evidence = (
        len(fcs) == 1
        and fcs[0].id == "no-evidence"
        and "did not converge" in fcs[0].query.lower()
    )

    if is_no_evidence:
        root_cause_summary = "Analyzer did not converge within max_steps."
        confidence = 0.2
    else:
        first_gap = fcs[0].expected_outcome if fcs else "(no failure case)"
        # Include notebook findings when available so downstream consumers have
        # the full signal (notebook findings may contain condensed phrasing).
        notebook_snippet = output.notebook_markdown.strip()
        if notebook_snippet:
            root_cause_summary = (
                f"Skill gap: {first_gap}\n\nNotebook findings:\n{notebook_snippet}"
            )
        else:
            root_cause_summary = f"Skill gap: {first_gap}"
        # Bump confidence with more cases up to 3.
        confidence = min(0.85, 0.5 + 0.15 * len(fcs))

    return {
        "anomaly_signal_id": anomaly_signal_id,
        "root_cause_summary": root_cause_summary,
        "evidence": {
            "notebook": output.notebook_markdown,
            "failure_case_ids": [fc.id for fc in fcs],
            "plan_steps_completed": output.plan_steps_completed,
            "total_iterations": output.total_iterations,
            "termination": output.notes,
        },
        "suggested_fix_type": SuggestedFixType.SUPPLEMENT_SOP,
        "suggested_fix_payload": {
            "failure_cases": [fc.model_dump() for fc in fcs],
        },
        "confidence_score": confidence,
        "status": RCAFindingStatus.PROPOSED,
    }
