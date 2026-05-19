def _create_agent(client):
    factory_id = client.post("/factories", json={"name": "F1", "deployment_type": "on_prem"}).json()["id"]
    return client.post("/agents", json={
        "factory_id": factory_id, "name": "A1", "purpose": "p", "runtime_status": "pending",
    }).json()["id"]


def test_create_anomaly_signal(client):
    agent_id = _create_agent(client)
    payload = {
        "agent_id": agent_id,
        "source_type": "metric_drift",
        "related_trace_refs": ["trace_001", "trace_002", "trace_003"],
        "status": "new",
    }
    response = client.post("/anomaly-signals", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_type"] == "metric_drift"
    assert len(body["related_trace_refs"]) == 3


def test_human_flag_signal(client):
    agent_id = _create_agent(client)
    payload = {
        "agent_id": agent_id,
        "source_type": "human_flag",
        "related_trace_refs": ["trace_xyz"],
        "status": "new",
    }
    response = client.post("/anomaly-signals", json=payload)
    assert response.status_code == 201
    assert response.json()["source_type"] == "human_flag"


def test_list_signals_for_agent(client):
    agent_id = _create_agent(client)
    client.post("/anomaly-signals", json={"agent_id": agent_id, "source_type": "metric_drift", "related_trace_refs": [], "status": "new"})
    client.post("/anomaly-signals", json={"agent_id": agent_id, "source_type": "cost_spike", "related_trace_refs": [], "status": "new"})
    response = client.get(f"/anomaly-signals?agent_id={agent_id}")
    assert response.status_code == 200
    assert len(response.json()) == 2
