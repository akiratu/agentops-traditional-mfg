def _create_signal(client):
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
    return client.post(
        "/anomaly-signals",
        json={
            "agent_id": agent_id,
            "source_type": "metric_drift",
            "related_trace_refs": [],
            "status": "new",
        },
    ).json()["id"]


def test_create_rca_finding(client):
    signal_id = _create_signal(client)
    payload = {
        "anomaly_signal_id": signal_id,
        "root_cause_summary": "New vendor X probe card firmware format not in RAG corpus.",
        "evidence": {"failed_traces": ["t1", "t2"], "skill_excerpt": "..."},
        "suggested_fix_type": "supplement_sop",
        "suggested_fix_payload": {"add_corpus": ["vendor_X_firmware.md"]},
        "confidence_score": 0.82,
        "status": "proposed",
    }
    response = client.post("/rca-findings", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["suggested_fix_type"] == "supplement_sop"
    assert body["confidence_score"] == 0.82
    assert body["status"] == "proposed"


def test_list_findings_for_signal(client):
    signal_id = _create_signal(client)
    client.post(
        "/rca-findings",
        json={
            "anomaly_signal_id": signal_id,
            "root_cause_summary": "...",
            "evidence": {},
            "suggested_fix_type": "prompt_change",
            "suggested_fix_payload": {},
            "confidence_score": 0.5,
            "status": "proposed",
        },
    )
    response = client.get(f"/rca-findings?anomaly_signal_id={signal_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_accept_finding(client):
    signal_id = _create_signal(client)
    finding_id = client.post(
        "/rca-findings",
        json={
            "anomaly_signal_id": signal_id,
            "root_cause_summary": "...",
            "evidence": {},
            "suggested_fix_type": "prompt_change",
            "suggested_fix_payload": {},
            "confidence_score": 0.5,
            "status": "proposed",
        },
    ).json()["id"]
    response = client.patch(
        f"/rca-findings/{finding_id}/status", json={"status": "accepted"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
