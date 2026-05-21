"""Seed the metal-mfg-rca-2026-05-20 demo data into a running backend so the
v0.5 UI has realistic content to display.

Usage:
    BACKEND=http://localhost:8000 python scripts/seed_metal_mfg_demo_for_ui.py

Prereqs:
    - Backend running (uvicorn agentops_core.main:app --port 8000)
    - Demo assets at docs/demo-assets/metal-mfg-rca-2026-05-20/

Output:
    Prints the URLs to open in the browser at http://localhost:3001.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError

BACKEND = os.environ.get("BACKEND", "http://localhost:8000")
ASSETS = Path(__file__).resolve().parent.parent / "docs/demo-assets/metal-mfg-rca-2026-05-20"


def post_json(path: str, body: dict, method: str = "POST") -> dict:
    url = f"{BACKEND}{path}"
    data = json.dumps(body).encode()
    req = urllib_request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method=method
    )
    try:
        with urllib_request.urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        sys.stderr.write(f"{method} {url} → {e.code}\n{e.read().decode()[:500]}\n")
        raise


def main() -> None:
    print(f"BACKEND={BACKEND}")
    print(f"ASSETS={ASSETS}")

    skill_data = json.loads((ASSETS / "03_skill_v1.json").read_text())
    trace_data = json.loads((ASSETS / "04_trace_analysis.json").read_text())

    # 1. Factory
    factory = post_json(
        "/factories",
        {
            "name": "ACME Metals (Demo)",
            "deployment_type": "on_prem",
            "kpi_targets": {
                "first_pass_yield_pct": 95.0,
                "scrap_rate_pct_max": 2.0,
            },
        },
    )
    print(f"✓ Factory: {factory['id']} — ACME Metals (Demo)")

    # 2. Agent
    agent = post_json(
        "/agents",
        {
            "factory_id": factory["id"],
            "name": "CNC RCA Agent",
            "purpose": "Diagnose CNC precision-machining quality anomalies via SOP-guided tool calls",
            "runtime_status": "running",
        },
    )
    print(f"✓ Agent:   {agent['id']} — CNC RCA Agent")

    # 3. Skill v1 (load from demo asset, override agent_id)
    skill_v1 = post_json(
        "/skills",
        {
            "agent_id": agent["id"],
            "version": 1,
            "status": "active",
            "prompt": skill_data["prompt"],
            "tool_specs": skill_data.get("tool_specs", []),
            "golden_test_cases": skill_data.get("golden_test_cases", []),
            "sop_source_set_id": skill_data.get(
                "sop_source_set_id", "set-metal-mfg-demo"
            ),
            "generated_by_run_id": skill_data.get(
                "generated_by_run_id", "run-metal-mfg-demo"
            ),
        },
    )
    print(f"✓ Skill v1: {skill_v1['id']} (status=active)")

    # 4. Link agent.current_skill_id → v1
    post_json(
        f"/agents/{agent['id']}/current-skill",
        {"current_skill_id": skill_v1["id"]},
        method="PATCH",
    )
    print(f"✓ Agent.current_skill_id linked to v1")

    # 5. Anomaly signal (status=resolved so finding is immediately visible)
    signal = post_json(
        "/anomaly-signals",
        {
            "agent_id": agent["id"],
            "source_type": "metric_drift",
            "related_trace_refs": ["27c64ba2", "0a034b14", "caffe926"],
            "status": "resolved",
        },
    )
    print(f"✓ Signal:  {signal['id']} (resolved, 3 traces)")

    # 6. RCAFinding (load from demo asset, override anomaly_signal_id)
    f_payload = trace_data["rca_finding"]
    finding = post_json(
        "/rca-findings",
        {
            "anomaly_signal_id": signal["id"],
            "root_cause_summary": f_payload["root_cause_summary"],
            "evidence": f_payload["evidence"],
            "suggested_fix_type": f_payload["suggested_fix_type"],
            "suggested_fix_payload": f_payload["suggested_fix_payload"],
            "confidence_score": f_payload["confidence_score"],
            "status": "proposed",
        },
    )
    print(
        f"✓ Finding: {finding['id']} (confidence "
        f"{finding['confidence_score']:.2f}, status={finding['status']})"
    )

    # Summary
    print("\n=== Ready to demo ===\n")
    ui = "http://localhost:3001"
    print(f"  Factories:       {ui}/factories")
    print(f"  Factory detail:  {ui}/factories/{factory['id']}")
    print(f"  Agent dashboard: {ui}/agents/{agent['id']}")
    print(f"  Anomaly feed:    {ui}/anomalies")
    print(f"  Finding hero:    {ui}/findings/{finding['id']}    ← the demo killer page")
    print(f"  Skill timeline:  {ui}/skills/{agent['id']}")
    print(
        f"\nTip: open the finding hero page first — it shows the 4-section notebook,\n"
        f"3 failure cases, and Accept → Self-Evolve button.\n"
    )


if __name__ == "__main__":
    main()
