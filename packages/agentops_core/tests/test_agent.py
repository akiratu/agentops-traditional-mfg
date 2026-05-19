def _create_factory(client):
    resp = client.post("/factories", json={"name": "F1", "deployment_type": "on_prem"})
    return resp.json()["id"]


def test_create_agent(client):
    factory_id = _create_factory(client)
    payload = {
        "factory_id": factory_id,
        "name": "RCA Agent",
        "purpose": "test floor incident root cause analysis",
        "runtime_status": "pending",
    }
    response = client.post("/agents", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "RCA Agent"
    assert body["factory_id"] == factory_id
    assert body["runtime_status"] == "pending"
    assert body["current_skill_id"] is None


def test_list_agents_for_factory(client):
    factory_id = _create_factory(client)
    client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "A1",
            "purpose": "p1",
            "runtime_status": "pending",
        },
    )
    client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "A2",
            "purpose": "p2",
            "runtime_status": "pending",
        },
    )
    response = client.get(f"/agents?factory_id={factory_id}")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_agent_not_found(client):
    response = client.get("/agents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
