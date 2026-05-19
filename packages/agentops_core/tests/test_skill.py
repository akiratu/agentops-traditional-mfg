def _setup(client):
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
    return factory_id, agent_id


def test_create_skill(client):
    _, agent_id = _setup(client)
    payload = {
        "agent_id": agent_id,
        "version": 1,
        "status": "draft",
        "prompt": "You are an RCA agent...",
        "tool_specs": [{"name": "query_mes", "description": "..."}],
        "golden_test_cases": [{"q": "test?", "a": "answer"}],
        "sop_source_set_id": "set-001",
    }
    response = client.post("/skills", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "draft"
    assert body["agent_id"] == agent_id


def test_list_skills_for_agent(client):
    _, agent_id = _setup(client)
    client.post(
        "/skills",
        json={
            "agent_id": agent_id,
            "version": 1,
            "status": "draft",
            "prompt": "v1",
            "tool_specs": [],
            "golden_test_cases": [],
            "sop_source_set_id": "set-001",
        },
    )
    client.post(
        "/skills",
        json={
            "agent_id": agent_id,
            "version": 2,
            "status": "active",
            "prompt": "v2",
            "tool_specs": [],
            "golden_test_cases": [],
            "sop_source_set_id": "set-002",
        },
    )
    response = client.get(f"/skills?agent_id={agent_id}")
    assert response.status_code == 200
    assert len(response.json()) == 2
