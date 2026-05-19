from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from agentops_core.services.langfuse_client import LangfuseTraceClient


def test_client_built_from_settings():
    """Settings produce a working client (we don't actually call Langfuse here)."""
    from agentops_core.config import Settings

    settings = Settings(
        langfuse_host="http://localhost:3000",
        langfuse_public_key="pk_test",
        langfuse_secret_key="sk_test",
    )
    client = LangfuseTraceClient.from_settings(settings)
    assert client.host == "http://localhost:3000"
    assert client.public_key == "pk_test"


def test_client_returns_empty_when_no_keys():
    """Without keys we still construct (graceful for dev)."""
    from agentops_core.config import Settings

    settings = Settings(
        langfuse_host="http://localhost:3000",
        langfuse_public_key="",
        langfuse_secret_key="",
    )
    client = LangfuseTraceClient.from_settings(settings)
    # is_available reflects whether we can actually talk to Langfuse
    assert client.is_available() is False


def test_fetch_trace_uses_underlying_sdk():
    fake_sdk = MagicMock()
    # MagicMock's `name` constructor arg names the mock itself — not a data attribute.
    # Set .name as a plain attribute after construction to avoid the collision.
    trace_data = MagicMock()
    trace_data.id = "trace_abc"
    trace_data.name = "rca_agent_session"
    trace_data.input = {"q": "yield drop"}
    trace_data.output = {"root_cause": "probe card"}
    trace_data.observations = []
    trace_data.metadata = {"agent_id": "agent-1"}
    fake_sdk.fetch_trace.return_value = MagicMock(data=trace_data)
    client = LangfuseTraceClient(
        host="http://localhost:3000",
        public_key="pk",
        secret_key="sk",
        sdk_client=fake_sdk,
    )
    trace = client.fetch_trace("trace_abc")
    assert trace["id"] == "trace_abc"
    assert trace["name"] == "rca_agent_session"
    assert trace["input"]["q"] == "yield drop"
    fake_sdk.fetch_trace.assert_called_once_with("trace_abc")


def test_search_traces_returns_list_of_summaries():
    fake_sdk = MagicMock()
    # MagicMock's `name` constructor arg names the mock — set as attribute post-construction.
    t1 = MagicMock()
    t1.id = "trace_1"
    t1.name = "rca"
    t1.timestamp = datetime.now(tz=UTC)
    t1.metadata = {"agent_id": "a1"}
    t2 = MagicMock()
    t2.id = "trace_2"
    t2.name = "rca"
    t2.timestamp = datetime.now(tz=UTC)
    t2.metadata = {"agent_id": "a1"}
    fake_sdk.fetch_traces.return_value = MagicMock(data=[t1, t2])
    client = LangfuseTraceClient(
        host="http://localhost:3000",
        public_key="pk",
        secret_key="sk",
        sdk_client=fake_sdk,
    )
    summaries = client.search_traces(
        agent_id="a1",
        since=datetime.now(tz=UTC) - timedelta(days=7),
        limit=10,
    )
    assert len(summaries) == 2
    assert summaries[0]["id"] == "trace_1"
