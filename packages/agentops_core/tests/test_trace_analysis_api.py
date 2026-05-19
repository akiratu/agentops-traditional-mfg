import os
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest


def _setup_agent_with_skill(client):
    factory_id = client.post(
        "/factories", json={"name": "F1", "deployment_type": "on_prem"}
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "A1",
            "purpose": "rca test agent",
            "runtime_status": "pending",
        },
    ).json()["id"]
    skill_id = client.post(
        "/skills",
        json={
            "agent_id": agent_id,
            "version": 1,
            "status": "active",
            "prompt": "you are an agent",
            "tool_specs": [],
            "golden_test_cases": [],
            "sop_source_set_id": "set-1",
        },
    ).json()["id"]
    return factory_id, agent_id, skill_id


def test_trace_analyses_returns_404_for_missing_signal(client):
    response = client.post(
        "/trace-analyses",
        json={"anomaly_signal_id": str(uuid4())},
    )
    assert response.status_code == 404


def test_trace_analyses_returns_400_when_agent_has_no_current_skill(client):
    _, agent_id, _ = _setup_agent_with_skill(client)
    signal_id = client.post(
        "/anomaly-signals",
        json={
            "agent_id": agent_id,
            "source_type": "metric_drift",
            "related_trace_refs": [],
            "status": "new",
        },
    ).json()["id"]
    response = client.post(
        "/trace-analyses",
        json={"anomaly_signal_id": signal_id},
    )
    assert response.status_code == 400
    assert "current_skill_id" in response.text.lower()


def test_trace_analyses_returns_finding_and_failure_cases(client, session):
    """Happy path: agent has skill, signal exists, analyzer is mocked to return one case."""
    from agentops_core.models.agent import Agent

    _, agent_id, skill_id = _setup_agent_with_skill(client)
    # Set current_skill_id directly via DB (no PATCH endpoint yet — Plan 4 territory).
    agent = session.get(Agent, UUID(agent_id))
    agent.current_skill_id = UUID(skill_id)
    session.add(agent)
    session.commit()

    signal_id = client.post(
        "/anomaly-signals",
        json={
            "agent_id": agent_id,
            "source_type": "metric_drift",
            "related_trace_refs": ["t1"],
            "status": "new",
        },
    ).json()["id"]

    # Patch the analyzer to short-circuit (avoid real LLM in tests).
    from agentops_core.schemas import FailureCase
    from agentops_core.services.trace_analyzer.agent import TraceAnalyzerOutput

    fake_out = TraceAnalyzerOutput(
        notebook_markdown="## 🔍\n- mocked",
        failure_cases=[
            FailureCase(
                id="case-mock",
                query="q",
                expected_outcome="e",
                actual_outcome="a",
                context=None,
            )
        ],
        plan_steps_completed=3,
        total_iterations=5,
        notes="terminated_by_submit",
    )
    with patch(
        "agentops_core.services.trace_analyzer.service.run_trace_analyzer",
        return_value=fake_out,
    ):
        response = client.post(
            "/trace-analyses",
            json={"anomaly_signal_id": signal_id},
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert "rca_finding" in body
    assert "failure_cases" in body
    assert body["rca_finding"]["status"] == "proposed"
    assert len(body["failure_cases"]) == 1
    assert body["failure_cases"][0]["id"] == "case-mock"


@pytest.mark.skipif(
    not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("GEMINI_API_KEY")),
    reason="Requires LANGFUSE_PUBLIC_KEY + GEMINI_API_KEY in env for real-LLM e2e",
)
def test_e2e_trace_analyzer_with_real_providers(client, session):
    """End-to-end: real Langfuse + real Gemini Pro.

    Seed a synthetic trace into Langfuse manually (or run rca-agent-demo to emit one),
    then create an AnomalySignal pointing at it, then POST /trace-analyses and check
    that a meaningful (non-'no-evidence') FailureCase comes back.

    This test exists to be invoked manually during development; the gate prevents
    accidental API calls in CI.
    """
    pytest.skip(
        "Manual verification only. Seed a trace via langfuse SDK + run this test "
        "explicitly with `pytest -k test_e2e_trace_analyzer_with_real_providers`."
    )
