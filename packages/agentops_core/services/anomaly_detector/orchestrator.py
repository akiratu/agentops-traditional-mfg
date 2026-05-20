"""Orchestrator placeholders. Full implementation in Plan 4 Task 11."""
from __future__ import annotations

import logging
from uuid import UUID

log = logging.getLogger(__name__)


def run_self_evolve_for_finding(*, finding_id: UUID) -> None:
    """Will dispatch /self-evolutions for the FailureCases on this finding."""
    log.warning(
        "orchestrator.run_self_evolve_for_finding(%s) is a placeholder. "
        "Implement in Plan 4 Task 11.",
        finding_id,
    )


def run_trace_analyzer_for_signal(*, signal_id: UUID) -> None:
    """Will dispatch /trace-analyses for a NEW AnomalySignal."""
    log.warning(
        "orchestrator.run_trace_analyzer_for_signal(%s) is a placeholder. "
        "Implement in Plan 4 Task 11.",
        signal_id,
    )
