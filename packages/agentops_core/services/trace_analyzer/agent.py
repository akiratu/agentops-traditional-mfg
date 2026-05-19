"""Trace Analyzer agent: ReAct loop that produces FailureCase[] from Langfuse traces.

Implementation lives in Task 6 of Plan 3. This skeleton exposes the public
interface so other modules (service, API) can import it stably.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from agentops_core.schemas import FailureCase


@dataclass
class TraceAnalyzerInput:
    anomaly_signal_id: UUID
    agent_id: UUID
    skill_id: UUID
    related_trace_refs: list[str]


@dataclass
class TraceAnalyzerOutput:
    notebook_markdown: str
    failure_cases: list[FailureCase]
    plan_steps_completed: int
    total_iterations: int
    notes: str = ""


PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_system_prompt() -> str:
    return (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")


def run_trace_analyzer(
    inputs: TraceAnalyzerInput,
    *,
    openai_client: Any,
    model: str,
    tool_registry: dict[str, Any],
    max_steps: int = 12,
) -> TraceAnalyzerOutput:
    """ReAct loop — implementation in Task 6.

    Returns at least one FailureCase (or a no-evidence placeholder) when done.
    """
    raise NotImplementedError("implemented in Plan 3 Task 6")
