def _create_agent(client):
    factory_id = client.post(
        "/factories", json={"name": "F1", "deployment_type": "on_prem"}
    ).json()["id"]
    return client.post(
        "/agents",
        json={
            "factory_id": factory_id, "name": "A1", "purpose": "p",
            "runtime_status": "pending",
        },
    ).json()["id"]


def test_human_flag_creates_anomaly_signal(client):
    agent_id = _create_agent(client)
    response = client.post(
        "/human-flags",
        json={
            "agent_id": agent_id,
            "trace_id": "trace_abc",
            "comment": "領班說這個診斷結果不對",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_type"] == "human_flag"
    assert body["agent_id"] == agent_id
    assert "trace_abc" in body["related_trace_refs"]
    assert body["status"] == "new"


def test_human_flag_unknown_agent_returns_404(client):
    response = client.post(
        "/human-flags",
        json={
            "agent_id": "00000000-0000-0000-0000-000000000000",
            "trace_id": "trace_abc",
        },
    )
    assert response.status_code == 404


def test_human_flag_without_comment_still_works(client):
    agent_id = _create_agent(client)
    response = client.post(
        "/human-flags",
        json={"agent_id": agent_id, "trace_id": "trace_xyz"},
    )
    assert response.status_code == 201
