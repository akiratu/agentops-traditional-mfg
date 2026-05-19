from uuid import uuid4

from agentops_core.models.rca_finding import RCAFindingStatus, SuggestedFixType
from agentops_core.schemas import FailureCase
from agentops_core.services.trace_analyzer.agent import TraceAnalyzerOutput
from agentops_core.services.trace_analyzer.output import (
    build_rca_finding_payload,
)


def test_build_finding_payload_with_failure_cases():
    out = TraceAnalyzerOutput(
        notebook_markdown="## 🔍\n- Found vendor X firmware mismatch\n",
        failure_cases=[
            FailureCase(
                id="case-vendor-x",
                query="yield dropped",
                expected_outcome="flag vendor X firmware version mismatch",
                actual_outcome="generic answer",
                context="trace_id=t1",
            )
        ],
        plan_steps_completed=4,
        total_iterations=7,
        notes="terminated_by_submit",
    )
    signal_id = uuid4()
    payload = build_rca_finding_payload(out, anomaly_signal_id=signal_id)
    assert payload["anomaly_signal_id"] == signal_id
    assert "vendor X firmware mismatch" in payload["root_cause_summary"]
    assert payload["suggested_fix_type"] == SuggestedFixType.SUPPLEMENT_SOP
    assert 0 <= payload["confidence_score"] <= 1
    assert payload["status"] == RCAFindingStatus.PROPOSED
    assert "evidence" in payload
    assert payload["evidence"]["failure_case_ids"] == ["case-vendor-x"]


def test_build_finding_payload_with_no_evidence_case_uses_low_confidence():
    out = TraceAnalyzerOutput(
        notebook_markdown="",
        failure_cases=[
            FailureCase(
                id="no-evidence",
                query="(analyzer did not converge)",
                expected_outcome="...",
                actual_outcome="...",
                context=None,
            )
        ],
        plan_steps_completed=0,
        total_iterations=12,
        notes="max_steps_or_empty_response",
    )
    payload = build_rca_finding_payload(out, anomaly_signal_id=uuid4())
    assert payload["confidence_score"] < 0.3  # low confidence for fallback
    assert payload["status"] == RCAFindingStatus.PROPOSED
