"""Trace Analyzer agent: ReAct loop that produces FailureCase[] from Langfuse traces.

Implementation: openai-SDK-driven multi-turn tool-calling loop.

Why openai SDK? It's the only SDK that natively supports Gemini (via openai-compat
base_url), OpenAI, and Ollama (via openai-compat base_url) — three providers we
need for Trace Analyzer reliability. Anthropic is out of scope for v0.1.

The agent state machine is:
- Each turn we send: system_prompt + accumulated [assistant_messages + tool_results]
- LLM responds with one or more tool_calls
- For each non-terminal tool call: dispatch via tool_registry, append result
- For 'submit_failure_cases': parse arguments, save to output, break loop
- For 'submit_plan' / 'mark_plan_step_done' / 'update_notebook': handled inline
  by the agent (no registry dispatch needed — they're state-mutation operations)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from agentops_core.schemas import FailureCase
from agentops_core.services.trace_analyzer.db_tools import DB_TOOL_SCHEMAS
from agentops_core.services.trace_analyzer.tools import LANGFUSE_TOOL_SCHEMAS

log = logging.getLogger(__name__)


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


_TERMINAL_NOTEBOOK_PLACEHOLDER = (
    "## 🔍 已查到什麼\n- (notebook not updated by agent)\n\n"
    "## 💡 目前推論\n資料不足\n\n"
    "## ❓ 還需驗證\n\n"
    "## 🚫 已排除\n"
)


# Schema for the terminal tool that ends the loop.
SUBMIT_FAILURE_CASES_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "submit_failure_cases",
        "description": "Terminate the analysis by submitting 1-3 FailureCases.",
        "parameters": {
            "type": "object",
            "properties": {
                "failure_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "query": {"type": "string"},
                            "expected_outcome": {"type": "string"},
                            "actual_outcome": {"type": "string"},
                            "context": {"type": ["string", "null"]},
                        },
                        "required": [
                            "id",
                            "query",
                            "expected_outcome",
                            "actual_outcome",
                        ],
                    },
                },
            },
            "required": ["failure_cases"],
        },
    },
}

INLINE_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "submit_plan",
            "description": "Declare a 3-5 step investigation plan upfront.",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_plan_step_done",
            "description": "Mark plan step `idx` (0-based) as complete.",
            "parameters": {
                "type": "object",
                "properties": {"idx": {"type": "integer"}},
                "required": ["idx"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_notebook",
            "description": "Replace the 4-section notebook with new content.",
            "parameters": {
                "type": "object",
                "properties": {"markdown": {"type": "string"}},
                "required": ["markdown"],
            },
        },
    },
]


def all_tool_schemas() -> list[dict[str, Any]]:
    return (
        INLINE_TOOL_SCHEMAS
        + LANGFUSE_TOOL_SCHEMAS
        + DB_TOOL_SCHEMAS
        + [SUBMIT_FAILURE_CASES_SCHEMA]
    )


def run_trace_analyzer(
    inputs: TraceAnalyzerInput,
    *,
    openai_client: Any,
    model: str,
    tool_registry: dict[str, Callable[..., Any]],
    max_steps: int = 12,
) -> TraceAnalyzerOutput:
    """Run the agent loop.

    Args:
        openai_client: an openai.OpenAI-style client (has .chat.completions.create).
        model: model name string passed to the client.
        tool_registry: maps tool_name -> callable(**args). External tools only
            (search_traces, fetch_trace_detail, fetch_skill_detail, etc.).
            Inline tools (submit_plan, update_notebook) are handled by this loop.
    """
    system_prompt = load_system_prompt()
    user_prompt = _initial_user_prompt(inputs)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    plan: list[str] = []
    plan_steps_done: set[int] = set()
    notebook: str = _TERMINAL_NOTEBOOK_PLACEHOLDER
    failure_cases: list[FailureCase] = []
    terminated_by_submit = False
    iteration = 0

    for iteration in range(1, max_steps + 1):
        try:
            resp = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=all_tool_schemas(),
                tool_choice="auto",
            )
        except Exception as exc:
            log.warning(
                "Trace Analyzer LLM call failed at iteration %d: %s", iteration, exc
            )
            break

        assistant_msg = resp.choices[0].message
        tool_calls = getattr(assistant_msg, "tool_calls", None) or []

        # Append assistant turn to history
        messages.append(
            {
                "role": "assistant",
                "content": getattr(assistant_msg, "content", None) or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        if not tool_calls:
            # Model returned content with no tool calls — break to avoid infinite loop
            log.info(
                "Trace Analyzer: model returned no tool calls at iter %d, terminating",
                iteration,
            )
            break

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            if name == "submit_failure_cases":
                failure_cases = _parse_failure_cases(args.get("failure_cases", []))
                terminated_by_submit = True
                tool_result = {"status": "terminated"}
            elif name == "submit_plan":
                plan = list(args.get("steps", []))
                tool_result = {"status": "ok", "plan_steps": len(plan)}
            elif name == "mark_plan_step_done":
                idx = args.get("idx")
                if isinstance(idx, int) and 0 <= idx < len(plan):
                    plan_steps_done.add(idx)
                tool_result = {"status": "ok", "done": sorted(plan_steps_done)}
            elif name == "update_notebook":
                notebook = args.get("markdown", notebook)
                tool_result = {"status": "ok"}
            elif name in tool_registry:
                try:
                    tool_result = tool_registry[name](**args)
                except Exception as exc:
                    tool_result = {"error": str(exc)}
            else:
                tool_result = {"error": f"unknown tool: {name}"}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                }
            )

        if terminated_by_submit:
            break

    if not failure_cases:
        # Fallback: no submit_failure_cases call within budget
        failure_cases = [
            FailureCase(
                id="no-evidence",
                query="(analyzer did not converge)",
                expected_outcome=(
                    "Analyzer should have produced at least one FailureCase. "
                    "Either max_steps was too low or traces did not show clear failures."
                ),
                actual_outcome=f"Loop exited after {iteration} iterations without submission.",
                context=f"anomaly_signal_id={inputs.anomaly_signal_id}",
            )
        ]

    return TraceAnalyzerOutput(
        notebook_markdown=notebook,
        failure_cases=failure_cases,
        plan_steps_completed=len(plan_steps_done),
        total_iterations=iteration,
        notes=(
            "terminated_by_submit"
            if terminated_by_submit
            else "max_steps_or_empty_response"
        ),
    )


def _initial_user_prompt(inp: TraceAnalyzerInput) -> str:
    return (
        "[INVESTIGATION REQUEST]\n"
        f"anomaly_signal_id: {inp.anomaly_signal_id}\n"
        f"agent_id: {inp.agent_id}\n"
        f"skill_id: {inp.skill_id}\n"
        f"related_trace_refs ({len(inp.related_trace_refs)}): "
        f"{inp.related_trace_refs}\n\n"
        "Start by calling submit_plan with 3-5 investigation steps. Then use the "
        "Langfuse and DB tools to dig in. When you've identified the failure pattern, "
        "call submit_failure_cases. Use the notebook tool to track findings."
    )


def _parse_failure_cases(raw: list[dict[str, Any]]) -> list[FailureCase]:
    out: list[FailureCase] = []
    for r in raw:
        try:
            out.append(FailureCase(**r))
        except Exception as exc:
            log.warning("failed to parse failure case %r: %s", r, exc)
    return out
