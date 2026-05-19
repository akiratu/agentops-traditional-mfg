import io

import pytest


def test_e2e_factory_to_skill_v1(client):
    """Deterministic e2e: factory → agent → SOP upload → Skill v1.

    Stops before Self-Evolve because the deterministic FakeLLMProvider
    cannot produce structured analysis output (see Task 10 skip reason).
    """
    # 1. Factory
    factory = client.post(
        "/factories",
        json={
            "name": "IC Test Floor",
            "deployment_type": "on_prem",
            "kpi_targets": {"yield_pct": 95.0},
        },
    ).json()
    factory_id = factory["id"]

    # 2. Agent
    agent = client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "RCA Agent",
            "purpose": "Yield drop root cause analysis across IT/OT",
            "runtime_status": "pending",
        },
    ).json()
    agent_id = agent["id"]

    # 3. Upload SOP
    md = b"""# Yield Drop Root Cause Analysis

## When to invoke

When yield in a 4-hour window drops more than 10 percentage points
from baseline, OR when a single bin (e.g., Bin 5) shows a sudden spike.

## Procedure

1. Query MES bin distribution for the affected product in the last 4 hours.
   Look for clustering by tester ID or by lot.
2. If clustering by tester, query the probe card health for that tester:
   - Touchdown count vs lifespan
   - Contact resistance trend
3. If probe card looks fine, query tester firmware version and
   compare against the known-good baseline.
4. Cross-check with OT systems: facility power events, compressor health.
"""
    sop = client.post(
        f"/factories/{factory_id}/sop-uploads",
        files={"file": ("rca.md", io.BytesIO(md), "text/markdown")},
        data={"type": "qc_spec"},
    ).json()

    # 4. Generate Skill v1
    skill_v1 = client.post(
        "/skill-generations",
        json={"agent_id": agent_id, "sop_source_ids": [sop["id"]]},
    ).json()
    assert skill_v1["version"] == 1
    assert skill_v1["status"] == "draft"
    # generated_by_run_id is a relative path like "skills/f2a-<hex>/<skill-name>"
    assert skill_v1["generated_by_run_id"].startswith("skills/f2a-")

    # 5. Verify Skill is queryable through /skills
    skills = client.get(f"/skills?agent_id={agent_id}").json()
    assert len(skills) == 1
    assert skills[0]["id"] == skill_v1["id"]


@pytest.mark.skip(
    reason="Full lifecycle including Self-Evolve requires real structured LLM "
    "output (not deterministic FakeLLMProvider). The deterministic parts are "
    "covered by test_e2e_factory_to_skill_v1 above; Self-Evolve guards (404/400) "
    "are covered by test_self_evolve.py. Run this manually against a real "
    "Anthropic/OpenAI provider to verify the full loop."
)
def test_full_lifecycle_factory_to_self_evolve(client):
    """Full lifecycle test — requires real LLM."""
    # 1. Factory
    factory = client.post(
        "/factories",
        json={
            "name": "IC Test Floor",
            "deployment_type": "on_prem",
            "kpi_targets": {"yield_pct": 95.0},
        },
    ).json()
    factory_id = factory["id"]

    # 2. Agent
    agent = client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "RCA Agent",
            "purpose": "Yield drop root cause analysis across IT/OT",
            "runtime_status": "pending",
        },
    ).json()
    agent_id = agent["id"]

    # 3. Upload SOP
    md = b"""# Yield Drop Root Cause Analysis

## When to invoke

When yield in a 4-hour window drops more than 10 percentage points
from baseline.

## Procedure

1. Query MES bin distribution.
2. Inspect probe card touchdown count.
3. Cross-check OT systems.
"""
    sop = client.post(
        f"/factories/{factory_id}/sop-uploads",
        files={"file": ("rca.md", io.BytesIO(md), "text/markdown")},
        data={"type": "qc_spec"},
    ).json()

    # 4. Generate Skill v1
    skill_v1 = client.post(
        "/skill-generations",
        json={"agent_id": agent_id, "sop_source_ids": [sop["id"]]},
    ).json()
    assert skill_v1["version"] == 1
    assert skill_v1["generated_by_run_id"].startswith("skills/f2a-")

    # 5. Self-Evolve with a failure case
    evolution = client.post(
        "/self-evolutions",
        json={
            "skill_id": skill_v1["id"],
            "failure_cases": [
                {
                    "id": "case-vendor-x",
                    "query": "Yield dropped on tester #7; new vendor X probe card",
                    "expected_outcome": (
                        "Identify vendor X firmware version mismatch "
                        "and recommend rollback or recalibration"
                    ),
                    "actual_outcome": (
                        "Generic answer; did not flag vendor X "
                        "as a possible firmware mismatch"
                    ),
                    "context": "vendor change deployed last week",
                }
            ],
        },
    ).json()
    skill_v2 = evolution["skill"]
    regression = evolution["regression_run"]

    assert skill_v2["version"] == 2
    assert skill_v2["agent_id"] == agent_id
    assert skill_v2["status"] == "draft"
    # generated_by_run_id is a relative path like "skills/f2a-evolve-<hex>/<skill-name>"
    assert skill_v2["generated_by_run_id"].startswith("skills/f2a-evolve-")

    assert regression["skill_id_old"] == skill_v1["id"]
    assert regression["skill_id_new"] == skill_v2["id"]
    assert regression["test_case_count"] >= 1

    # 6. Sanity: list skills for agent — should have v1 and v2
    skills = client.get(f"/skills?agent_id={agent_id}").json()
    assert len(skills) == 2
    versions = sorted(s["version"] for s in skills)
    assert versions == [1, 2]
