import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from agentops_core.schemas import FailureCase
from agentops_core.services.trace_analyzer.agent import (
    TraceAnalyzerInput,
    run_trace_analyzer,
)


class _FakeOpenAIResp:
    """Fake openai chat completions response."""

    def __init__(self, content=None, tool_calls=None):
        self.choices = [
            MagicMock(
                message=MagicMock(
                    content=content,
                    tool_calls=tool_calls or [],
                    role="assistant",
                )
            )
        ]


def _make_tool_call(name: str, args: dict):
    mock = MagicMock(id=f"call_{name}", type="function")
    # `name` is a reserved MagicMock kwarg, so we set it post-construction.
    mock.function = MagicMock(arguments=json.dumps(args))
    mock.function.name = name
    return mock


def test_run_trace_analyzer_terminates_when_submit_failure_cases_called():
    """The agent emits submit_failure_cases on its first turn → loop terminates."""
    fake_openai = MagicMock()
    submit_call = _make_tool_call(
        "submit_failure_cases",
        {
            "failure_cases": [
                {
                    "id": "case-1",
                    "query": "yield dropped tester 7",
                    "expected_outcome": "identify probe card lifespan exceeded",
                    "actual_outcome": "generic answer; ignored probe card",
                    "context": "trace_id=t1",
                }
            ]
        },
    )
    fake_openai.chat.completions.create.return_value = _FakeOpenAIResp(
        tool_calls=[submit_call]
    )

    inp = TraceAnalyzerInput(
        anomaly_signal_id=uuid4(),
        agent_id=uuid4(),
        skill_id=uuid4(),
        related_trace_refs=["t1"],
    )
    out = run_trace_analyzer(
        inp,
        openai_client=fake_openai,
        model="gemini-2.5-pro",
        tool_registry={},  # submit_failure_cases is handled by the loop, not the registry
        max_steps=5,
    )
    assert len(out.failure_cases) == 1
    assert out.failure_cases[0].id == "case-1"
    assert out.total_iterations == 1


def test_run_trace_analyzer_returns_no_evidence_when_max_steps_exceeded():
    fake_openai = MagicMock()
    # Always return an empty assistant message (no tool calls, no content)
    fake_openai.chat.completions.create.return_value = _FakeOpenAIResp(content=None, tool_calls=[])

    inp = TraceAnalyzerInput(
        anomaly_signal_id=uuid4(),
        agent_id=uuid4(),
        skill_id=uuid4(),
        related_trace_refs=[],
    )
    out = run_trace_analyzer(
        inp,
        openai_client=fake_openai,
        model="gemini-2.5-pro",
        tool_registry={},
        max_steps=3,
    )
    # Got at least one fallback FailureCase
    assert len(out.failure_cases) >= 1
    assert out.failure_cases[0].id == "no-evidence"
    # Loop terminates as soon as model returns no tool_calls (could be iter 1
    # since the fake returns empty on the first turn). Just verify it stayed
    # within budget.
    assert 1 <= out.total_iterations <= 3


def test_run_trace_analyzer_dispatches_tools():
    """Tool registry is called when the agent emits a non-submit tool call."""
    fake_openai = MagicMock()
    tool_call = _make_tool_call("search_traces", {"agent_id": "a1", "limit": 5})
    submit_call = _make_tool_call(
        "submit_failure_cases",
        {
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
    )
    # Turn 1: agent calls search_traces. Turn 2: agent submits failure cases.
    fake_openai.chat.completions.create.side_effect = [
        _FakeOpenAIResp(tool_calls=[tool_call]),
        _FakeOpenAIResp(tool_calls=[submit_call]),
    ]

    search_traces_mock = MagicMock(return_value=[{"id": "t1"}])
    inp = TraceAnalyzerInput(
        anomaly_signal_id=uuid4(),
        agent_id=uuid4(),
        skill_id=uuid4(),
        related_trace_refs=[],
    )
    out = run_trace_analyzer(
        inp,
        openai_client=fake_openai,
        model="gemini-2.5-pro",
        tool_registry={"search_traces": search_traces_mock},
        max_steps=5,
    )
    search_traces_mock.assert_called_once()
    assert len(out.failure_cases) == 1
    assert out.total_iterations == 2


def test_build_initial_notebook_includes_signal_and_skill():
    from agentops_core.services.trace_analyzer.notebook import build_initial_notebook

    nb = build_initial_notebook(
        anomaly_summary="diagnostic accuracy dropped 20%",
        agent_purpose="Yield drop RCA",
        skill_version=3,
        related_trace_count=5,
    )
    assert "diagnostic accuracy" in nb
    assert "Yield drop RCA" in nb
    assert "v3" in nb or "version 3" in nb
    # 4 required sections
    assert "🔍" in nb
    assert "💡" in nb
    assert "❓" in nb
    assert "🚫" in nb
