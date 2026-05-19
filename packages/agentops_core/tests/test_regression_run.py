def _create_two_skills(client):
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
    s1 = client.post(
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
    s2 = client.post(
        "/skills",
        json={
            "agent_id": agent_id,
            "version": 2,
            "status": "draft",
            "prompt": "v2",
            "tool_specs": [],
            "golden_test_cases": [],
            "sop_source_set_id": "s2",
        },
    ).json()["id"]
    return s1, s2


def test_create_regression_run(client):
    s1, s2 = _create_two_skills(client)
    payload = {
        "skill_id_old": s1,
        "skill_id_new": s2,
        "test_set_strategy": "mixed",
        "test_case_count": 10,
        "pass_count": 9,
        "fail_count": 1,
        "per_case_results": [
            {"id": "case_1", "pass": True},
            {"id": "case_2", "pass": False},
        ],
        "regression_findings": ["case_2 regressed on edge condition"],
        "verdict": "needs_review",
    }
    response = client.post("/regression-runs", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["pass_count"] == 9
    assert body["verdict"] == "needs_review"


def test_list_runs(client):
    s1, s2 = _create_two_skills(client)
    client.post(
        "/regression-runs",
        json={
            "skill_id_old": s1,
            "skill_id_new": s2,
            "test_set_strategy": "mixed",
            "test_case_count": 10,
            "pass_count": 10,
            "fail_count": 0,
            "per_case_results": [],
            "regression_findings": [],
            "verdict": "pass",
        },
    )
    response = client.get("/regression-runs")
    assert response.status_code == 200
    assert len(response.json()) == 1
