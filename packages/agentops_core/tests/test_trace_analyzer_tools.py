from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from agentops_core.services.trace_analyzer.tools import (
    LANGFUSE_TOOL_SCHEMAS,
    search_traces_tool,
    fetch_trace_detail_tool,
)


def _fake_client():
    client = MagicMock()
    client.search_traces.return_value = [
        {"id": "t1", "name": "rca", "timestamp": "2026-05-19T10:00:00", "metadata": {}},
        {"id": "t2", "name": "rca", "timestamp": "2026-05-19T11:00:00", "metadata": {}},
    ]
    client.fetch_trace.return_value = {
        "id": "t1",
        "name": "rca",
        "input": {"q": "yield drop tester 7"},
        "output": {"root_cause": "(LLM unavailable)"},
        "observations": [
            {"id": "obs1", "type": "LLM", "name": "Gemini", "input": "prompt", "output": "response"},
        ],
        "metadata": {"agent_id": "a-1"},
    }
    return client


def test_search_traces_tool_returns_dicts():
    client = _fake_client()
    out = search_traces_tool(client, agent_id="a-1", limit=5)
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0]["id"] == "t1"


def test_fetch_trace_detail_tool_returns_normalized_trace():
    client = _fake_client()
    out = fetch_trace_detail_tool(client, trace_id="t1")
    assert out["id"] == "t1"
    assert out["input"]["q"] == "yield drop tester 7"
    assert out["output"]["root_cause"] == "(LLM unavailable)"
    assert len(out["observations"]) == 1


def test_langfuse_tool_schemas_have_required_fields():
    # Each tool exposes an OpenAI-style function schema for the LLM
    for schema in LANGFUSE_TOOL_SCHEMAS:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn


def test_search_traces_tool_respects_since():
    client = _fake_client()
    since = datetime.now(tz=timezone.utc) - timedelta(days=3)
    search_traces_tool(client, agent_id="a-1", since=since, limit=5)
    # Verify we passed `since` through to the client
    call = client.search_traces.call_args
    assert call.kwargs.get("since") == since or (len(call.args) > 1 and call.args[1] == since)


from uuid import uuid4

from sqlmodel import Session

from agentops_core.models.agent import Agent, RuntimeStatus
from agentops_core.models.factory import Factory
from agentops_core.models.rca_finding import (
    RCAFinding,
    RCAFindingStatus,
    SuggestedFixType,
)
from agentops_core.models.skill import Skill, SkillStatus
from agentops_core.models.anomaly_signal import (
    AnomalySignal,
    AnomalySourceType,
    AnomalyStatus,
)
from agentops_core.services.trace_analyzer.db_tools import (
    DB_TOOL_SCHEMAS,
    fetch_past_findings_tool,
    fetch_skill_detail_tool,
    fetch_skill_versions_tool,
)


def _seed_skill(session: Session) -> tuple[Skill, Agent]:
    f = Factory(name="F1")
    session.add(f)
    session.commit()
    session.refresh(f)
    a = Agent(factory_id=f.id, name="A1", purpose="test", runtime_status=RuntimeStatus.PENDING)
    session.add(a)
    session.commit()
    session.refresh(a)
    s = Skill(
        agent_id=a.id,
        version=1,
        status=SkillStatus.ACTIVE,
        prompt="You are a helpful agent.",
        tool_specs=[],
        golden_test_cases=[],
        sop_source_set_id="set-1",
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    return s, a


def test_fetch_skill_detail_tool(session: Session):
    skill, _ = _seed_skill(session)
    out = fetch_skill_detail_tool(session, skill_id=skill.id)
    assert out["id"] == str(skill.id)
    assert out["version"] == 1
    assert out["status"] == "active"
    assert out["prompt"].startswith("You are")


def test_fetch_skill_detail_returns_none_when_missing(session: Session):
    missing = uuid4()
    out = fetch_skill_detail_tool(session, skill_id=missing)
    assert out is None


def test_fetch_skill_versions_tool_returns_history(session: Session):
    skill_v1, agent = _seed_skill(session)
    skill_v2 = Skill(
        agent_id=agent.id,
        version=2,
        status=SkillStatus.DRAFT,
        prompt="v2 prompt",
        tool_specs=[],
        golden_test_cases=[],
        sop_source_set_id="set-2",
    )
    session.add(skill_v2)
    session.commit()
    versions = fetch_skill_versions_tool(session, agent_id=agent.id)
    assert len(versions) == 2
    versions_sorted = sorted(versions, key=lambda v: v["version"])
    assert versions_sorted[0]["version"] == 1
    assert versions_sorted[1]["version"] == 2


def test_fetch_past_findings_tool_returns_recent(session: Session):
    skill, agent = _seed_skill(session)
    # Seed a signal + a finding
    signal = AnomalySignal(
        agent_id=agent.id,
        source_type=AnomalySourceType.METRIC_DRIFT,
        related_trace_refs=["t-prior"],
        status=AnomalyStatus.RESOLVED,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    finding = RCAFinding(
        anomaly_signal_id=signal.id,
        root_cause_summary="prior root cause",
        evidence={},
        suggested_fix_type=SuggestedFixType.PROMPT_CHANGE,
        suggested_fix_payload={},
        confidence_score=0.7,
        status=RCAFindingStatus.ACCEPTED,
    )
    session.add(finding)
    session.commit()
    out = fetch_past_findings_tool(session, agent_id=agent.id, k=3)
    assert len(out) == 1
    assert out[0]["root_cause_summary"] == "prior root cause"


def test_db_tool_schemas_have_required_fields():
    for schema in DB_TOOL_SCHEMAS:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
