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
    skill = client.post(
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
    ).json()
    return agent_id, skill["id"]


def test_patch_agent_current_skill(client):
    agent_id, skill_id = _setup(client)
    response = client.patch(
        f"/agents/{agent_id}/current-skill",
        json={"current_skill_id": skill_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_skill_id"] == skill_id


def test_patch_agent_current_skill_clears(client):
    agent_id, skill_id = _setup(client)
    client.patch(
        f"/agents/{agent_id}/current-skill",
        json={"current_skill_id": skill_id},
    )
    response = client.patch(
        f"/agents/{agent_id}/current-skill",
        json={"current_skill_id": None},
    )
    assert response.status_code == 200
    assert response.json()["current_skill_id"] is None


def test_patch_agent_current_skill_agent_not_found(client):
    response = client.patch(
        "/agents/00000000-0000-0000-0000-000000000000/current-skill",
        json={"current_skill_id": None},
    )
    assert response.status_code == 404


def test_patch_agent_current_skill_skill_not_found(client):
    agent_id, _ = _setup(client)
    response = client.patch(
        f"/agents/{agent_id}/current-skill",
        json={"current_skill_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 400
