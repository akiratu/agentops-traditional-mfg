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


def test_patch_runtime_status_to_running(client):
    agent_id = _create_agent(client)
    response = client.patch(
        f"/agents/{agent_id}/runtime-status",
        json={"runtime_status": "running"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["runtime_status"] == "running"
    assert body["deployed_at"] is not None


def test_patch_runtime_status_stopped_keeps_deployed_at(client):
    agent_id = _create_agent(client)
    client.patch(
        f"/agents/{agent_id}/runtime-status",
        json={"runtime_status": "running"},
    )
    response = client.patch(
        f"/agents/{agent_id}/runtime-status",
        json={"runtime_status": "stopped"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["runtime_status"] == "stopped"
    assert body["deployed_at"] is not None


def test_patch_runtime_status_invalid(client):
    agent_id = _create_agent(client)
    response = client.patch(
        f"/agents/{agent_id}/runtime-status",
        json={"runtime_status": "banana"},
    )
    assert response.status_code == 422


def test_patch_runtime_status_agent_not_found(client):
    response = client.patch(
        "/agents/00000000-0000-0000-0000-000000000000/runtime-status",
        json={"runtime_status": "running"},
    )
    assert response.status_code == 404
