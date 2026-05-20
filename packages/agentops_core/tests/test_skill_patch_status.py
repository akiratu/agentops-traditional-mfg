def _setup_two_skills(client):
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
    v1 = client.post(
        "/skills",
        json={
            "agent_id": agent_id, "version": 1, "status": "active",
            "prompt": "v1", "tool_specs": [], "golden_test_cases": [],
            "sop_source_set_id": "s1",
        },
    ).json()
    v2 = client.post(
        "/skills",
        json={
            "agent_id": agent_id, "version": 2, "status": "draft",
            "prompt": "v2", "tool_specs": [], "golden_test_cases": [],
            "sop_source_set_id": "s2",
        },
    ).json()
    return v1, v2, agent_id


def test_patch_skill_status_to_active(client):
    _, v2, _ = _setup_two_skills(client)
    response = client.patch(f"/skills/{v2['id']}/status", json={"status": "active"})
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_promote_to_active_archives_previous_active(client):
    v1, v2, agent_id = _setup_two_skills(client)
    response = client.patch(f"/skills/{v2['id']}/status", json={"status": "active"})
    assert response.status_code == 200

    # v1 should now be archived (auto-demoted)
    v1_after = client.get(f"/skills/{v1['id']}").json()
    assert v1_after["status"] == "archived"


def test_patch_skill_status_invalid_value(client):
    _, v2, _ = _setup_two_skills(client)
    response = client.patch(f"/skills/{v2['id']}/status", json={"status": "banana"})
    assert response.status_code == 422


def test_patch_skill_status_not_found(client):
    response = client.patch(
        "/skills/00000000-0000-0000-0000-000000000000/status",
        json={"status": "active"},
    )
    assert response.status_code == 404
