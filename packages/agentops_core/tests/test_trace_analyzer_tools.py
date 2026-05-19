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
