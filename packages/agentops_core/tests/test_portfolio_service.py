"""Tests for POST /portfolio-generations."""
from __future__ import annotations

import io

import pytest


def _setup(client, sop_blobs: list[tuple[str, bytes]]):
    factory_id = client.post(
        "/factories", json={"name": "F1", "deployment_type": "on_prem"}
    ).json()["id"]
    sop_ids = []
    for name, blob in sop_blobs:
        resp = client.post(
            f"/factories/{factory_id}/sop-uploads",
            files={"file": (name, io.BytesIO(blob), "text/markdown")},
            data={"type": "qc_spec"},
        )
        assert resp.status_code == 201
        sop_ids.append(resp.json()["id"])
    return factory_id, sop_ids


@pytest.mark.skip(
    reason=(
        "portfolio decomposer requires real structured-output LLM; "
        "FakeLLMProvider returns {} which fails PortfolioPlan validation after "
        "MAX_ATTEMPTS=4 retries. See e2e test in Task 11."
    )
)
def test_generate_portfolio_returns_plan(client):
    md1 = b"# RCA SOP\n\n## When yield drops\n\n1. Check bin distribution\n2. Inspect probe card\n"
    md2 = b"# Process Optimization SOP\n\n## Tuning\n\n1. Adjust temperature\n2. Re-test\n"
    factory_id, sop_ids = _setup(client, [("rca.md", md1), ("process.md", md2)])

    response = client.post(
        "/portfolio-generations",
        json={
            "factory_id": factory_id,
            "sop_source_ids": sop_ids,
            "description": "Manufacturing AI agents for an IC test factory",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "agents" in body
    assert isinstance(body["agents"], list)
    assert len(body["agents"]) >= 1
    for agent in body["agents"]:
        assert "id" in agent
        assert "name" in agent
        assert "skill_ids" in agent
        assert isinstance(agent["skill_ids"], list)


def test_generate_portfolio_requires_factory(client):
    response = client.post(
        "/portfolio-generations",
        json={
            "factory_id": "00000000-0000-0000-0000-000000000000",
            "sop_source_ids": [],
            "description": "x",
        },
    )
    assert response.status_code == 404
