from datetime import UTC, datetime
from unittest.mock import MagicMock

from agentops_core.services.langfuse_client import LangfuseTraceClient


def _trace_mock(trace_id: str, scores: list[dict]):
    m = MagicMock()
    m.id = trace_id
    m.timestamp = datetime.now(tz=UTC)
    m.metadata = {}
    m.scores = scores
    # `name` is a reserved MagicMock kwarg; assign post-construction.
    m.name = "rca"
    return m


def test_search_traces_only_failures_filters_by_score():
    fake_sdk = MagicMock()
    fake_sdk.fetch_traces.return_value = MagicMock(
        data=[
            _trace_mock("t1_pass", [{"name": "rca_accuracy", "value": 1.0}]),
            _trace_mock("t2_fail", [{"name": "rca_accuracy", "value": 0.0}]),
            _trace_mock("t3_partial", [{"name": "rca_accuracy", "value": 0.4}]),
            _trace_mock("t4_unknown", []),  # no scores → not a failure by default
        ]
    )
    client = LangfuseTraceClient(
        host="http://localhost:3000",
        public_key="pk",
        secret_key="sk",
        sdk_client=fake_sdk,
    )
    results = client.search_traces(agent_id="a1", only_failures=True, limit=10)
    ids = [r["id"] for r in results]
    assert "t1_pass" not in ids
    assert "t2_fail" in ids
    assert "t3_partial" in ids
    assert "t4_unknown" not in ids


def test_search_traces_default_does_not_filter():
    fake_sdk = MagicMock()
    fake_sdk.fetch_traces.return_value = MagicMock(
        data=[
            _trace_mock("t1_pass", [{"name": "rca_accuracy", "value": 1.0}]),
            _trace_mock("t2_fail", [{"name": "rca_accuracy", "value": 0.0}]),
        ]
    )
    client = LangfuseTraceClient(
        host="http://localhost:3000",
        public_key="pk",
        secret_key="sk",
        sdk_client=fake_sdk,
    )
    results = client.search_traces(agent_id="a1", limit=10)
    assert len(results) == 2
