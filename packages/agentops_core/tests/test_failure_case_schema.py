import pytest
from pydantic import ValidationError

from agentops_core.schemas import FailureCase


def test_failure_case_minimal():
    fc = FailureCase(
        id="case-001",
        query="Yield dropped to 78% — what's the root cause?",
        expected_outcome="Identify probe card touchdown count exceeded lifespan",
        actual_outcome="Generic answer; did not check probe card",
    )
    assert fc.id == "case-001"
    assert fc.context is None


def test_failure_case_with_context():
    fc = FailureCase(
        id="case-002",
        query="...",
        expected_outcome="...",
        actual_outcome="...",
        context="trace_id=trace_abc; agent_skill_version=3",
    )
    assert fc.context.startswith("trace_id=")


def test_failure_case_requires_id():
    with pytest.raises(ValidationError):
        FailureCase(
            query="x",
            expected_outcome="y",
            actual_outcome="z",
        )  # missing id
