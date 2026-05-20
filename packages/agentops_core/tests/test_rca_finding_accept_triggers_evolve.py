from unittest.mock import patch


def _setup_finding(client, session):
    """Create factory, agent (with current_skill), signal, finding."""

    factory_id = client.post(
        "/factories", json={"name": "F1", "deployment_type": "on_prem"}
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "A1",
            "purpose": "p",
            "runtime_status": "pending",
        },
    ).json()["id"]
    skill_id = client.post(
        "/skills",
        json={
            "agent_id": agent_id,
            "version": 1,
            "status": "active",
            "prompt": "v1",
            "tool_specs": [],
            "golden_test_cases": [],
            "sop_source_set_id": "s1",
        },
    ).json()["id"]
    # Wire agent.current_skill_id via the new PATCH endpoint
    client.patch(
        f"/agents/{agent_id}/current-skill",
        json={"current_skill_id": skill_id},
    )

    signal_id = client.post(
        "/anomaly-signals",
        json={
            "agent_id": agent_id,
            "source_type": "metric_drift",
            "related_trace_refs": ["t1"],
            "status": "new",
        },
    ).json()["id"]

    finding = client.post(
        "/rca-findings",
        json={
            "anomaly_signal_id": signal_id,
            "root_cause_summary": "test",
            "evidence": {},
            "suggested_fix_type": "supplement_sop",
            "suggested_fix_payload": {
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
            "confidence_score": 0.85,
            "status": "proposed",
        },
    ).json()
    return finding["id"], skill_id


def test_accepting_finding_dispatches_self_evolve(client, session):
    finding_id, skill_id = _setup_finding(client, session)
    with patch(
        "agentops_core.api.rca_finding.dispatch_self_evolve_background"
    ) as mock_dispatch:
        response = client.patch(
            f"/rca-findings/{finding_id}/status",
            json={"status": "accepted"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    mock_dispatch.assert_called_once()
    args, kwargs = mock_dispatch.call_args
    called_finding_id = kwargs.get("finding_id") or (args[0] if args else None)
    assert str(called_finding_id) == str(finding_id)


def test_rejecting_finding_does_not_dispatch(client, session):
    finding_id, _ = _setup_finding(client, session)
    with patch(
        "agentops_core.api.rca_finding.dispatch_self_evolve_background"
    ) as mock_dispatch:
        response = client.patch(
            f"/rca-findings/{finding_id}/status",
            json={"status": "rejected"},
        )
    assert response.status_code == 200
    mock_dispatch.assert_not_called()
