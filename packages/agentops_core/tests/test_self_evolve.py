import io

import pytest


def _setup_skill(client):
    """Create a factory + agent + SOP + initial skill, return (skill_id, agent_id)."""
    factory_id = client.post(
        "/factories", json={"name": "F1", "deployment_type": "on_prem"}
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "RCA Agent",
            "purpose": "Diagnose yield drop on test floor",
            "runtime_status": "pending",
        },
    ).json()["id"]
    md = (
        b"# Yield Drop RCA\n\n## Steps\n\n1. Check Bin 5 spike\n2. Inspect probe card\n"
    )
    sop_id = client.post(
        f"/factories/{factory_id}/sop-uploads",
        files={"file": ("rca.md", io.BytesIO(md), "text/markdown")},
        data={"type": "qc_spec"},
    ).json()["id"]
    skill = client.post(
        "/skill-generations",
        json={"agent_id": agent_id, "sop_source_ids": [sop_id]},
    ).json()
    return skill["id"], agent_id


@pytest.mark.skip(
    reason=(
        "Self-Evolve requires structured LLM output (analyses key); "
        "FakeLLMProvider returns {} causing AnalyzerError after MAX_ATTEMPTS=4 retries. "
        "See Plan 3 e2e with real Langfuse for end-to-end coverage."
    )
)
def test_self_evolve_creates_v2(client):
    skill_v1_id, agent_id = _setup_skill(client)

    failures = [
        {
            "id": "case-001",
            "query": "Yield dropped — new vendor X probe card",
            "expected_outcome": "Identify vendor X firmware version mismatch",
            "actual_outcome": "Generic answer; did not flag vendor X",
            "context": None,
        }
    ]
    response = client.post(
        "/self-evolutions",
        json={"skill_id": skill_v1_id, "failure_cases": failures},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "skill" in body
    assert "regression_run" in body
    assert body["skill"]["version"] == 2
    assert body["skill"]["status"] == "draft"
    # generated_by_run_id is a relative path like "skills/f2a-evolve-<hex>/<skill-name>"
    assert body["skill"]["generated_by_run_id"].startswith("skills/f2a-evolve-")
    assert body["regression_run"]["test_case_count"] >= 1


def test_self_evolve_unknown_skill_returns_404(client):
    response = client.post(
        "/self-evolutions",
        json={
            "skill_id": "00000000-0000-0000-0000-000000000000",
            "failure_cases": [],
        },
    )
    assert response.status_code == 404


def test_self_evolve_requires_at_least_one_failure(client):
    skill_id, _ = _setup_skill(client)
    response = client.post(
        "/self-evolutions",
        json={"skill_id": skill_id, "failure_cases": []},
    )
    assert response.status_code == 400
