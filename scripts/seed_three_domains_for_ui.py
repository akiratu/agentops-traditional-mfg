"""Seed all 3 government-plan domains into the running backend so the UI
demo proves the platform handles every domain on one stack.

Domains:
    1. ACME Metals — 金屬加工 CNC (Plan C, the actual government deliverable)
    2. XX Semi Test — 半導體封測 (Plan B technology integrated in)
    3. SI 客服中心 — 系統整合維修客服 (Plan A technology integrated in)

Each domain gets:
    - Factory (with kpi_targets per domain)
    - Agent (with deployment-relevant purpose)
    - Skill v1 (ACTIVE, real content from demo assets / SOP fixtures)
    - Agent.current_skill_id linked to v1

The metal-mfg domain also gets the full RCA finding chain (anomaly + finding
+ Self-Evolve v2 + regression) so the demo can showcase a complete loop.
The other 2 domains stay at "deployed, idle" — proving multi-tenant
hosting without bloating the demo with too many parallel stories.

Usage:
    BACKEND=http://localhost:8000 python scripts/seed_three_domains_for_ui.py

Prereqs:
    - Backend running (uvicorn agentops_core.main:app --port 8000)
    - Langfuse running (LLM_PROVIDER_NAME=google for real Self-Evolve, or
      fake for instant deterministic seed)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError

BACKEND = os.environ.get("BACKEND", "http://localhost:8000")
REPO = Path(__file__).resolve().parent.parent
METAL_ASSETS = REPO / "docs/demo-assets/metal-mfg-rca-2026-05-20"
SEMI_ASSETS = REPO / "docs/demo-assets/semiconductor-rca-2026-05-19"
SERVICE_SOP = (
    REPO / "packages/flows2agents/tests/fixtures/service-portfolio/mini-sop.md"
)


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
        sys.stderr.write(f"{method} {url} -> {e.code}\n{e.read().decode()[:500]}\n")
        raise


def seed_factory_agent_skill(
    *,
    factory_name: str,
    deployment_type: str,
    kpi_targets: dict,
    agent_name: str,
    agent_purpose: str,
    skill_payload: dict,
) -> tuple[dict, dict, dict]:
    factory = post_json(
        "/factories",
        {
            "name": factory_name,
            "deployment_type": deployment_type,
            "kpi_targets": kpi_targets,
        },
    )
    agent = post_json(
        "/agents",
        {
            "factory_id": factory["id"],
            "name": agent_name,
            "purpose": agent_purpose,
            "runtime_status": "running",
        },
    )
    skill = post_json(
        "/skills",
        {
            "agent_id": agent["id"],
            "version": 1,
            "status": "active",
            "prompt": skill_payload["prompt"],
            "tool_specs": skill_payload.get("tool_specs", []),
            "golden_test_cases": skill_payload.get("golden_test_cases", []),
            "sop_source_set_id": skill_payload.get(
                "sop_source_set_id", f"set-{factory_name.replace(' ', '-').lower()}"
            ),
            "generated_by_run_id": skill_payload.get(
                "generated_by_run_id", f"run-{factory_name.replace(' ', '-').lower()}"
            ),
        },
    )
    post_json(
        f"/agents/{agent['id']}/current-skill",
        {"current_skill_id": skill["id"]},
        method="PATCH",
    )
    return factory, agent, skill


def main() -> None:
    print(f"BACKEND={BACKEND}\n")

    # ----- 1) Metal mfg (Plan C, the headline deliverable) -----
    metal_skill = json.loads((METAL_ASSETS / "03_skill_v1.json").read_text())
    metal_trace = json.loads((METAL_ASSETS / "04_trace_analysis.json").read_text())

    factory_metal, agent_metal, skill_metal = seed_factory_agent_skill(
        factory_name="ACME Metals(金屬加工)",
        deployment_type="on_prem",
        kpi_targets={"first_pass_yield_pct": 95.0, "scrap_rate_pct_max": 2.0},
        agent_name="CNC RCA Agent",
        agent_purpose="CNC 精密加工異常根因分析:刀具磨損 / 熱變形 / 換班程式 / 材料批次",
        skill_payload=metal_skill,
    )
    print(f"[1/3] ACME Metals  factory={factory_metal['id'][:8]} agent={agent_metal['id'][:8]}")

    # Add full finding chain for metal so the demo has a complete loop on this domain
    sig_metal = post_json(
        "/anomaly-signals",
        {
            "agent_id": agent_metal["id"],
            "source_type": "metric_drift",
            "related_trace_refs": [
                "27c64ba2-f5b6-4f55-8dd3-7540f78f8fce",
                "0a034b14-2e1a-46fa-9bef-1a96d11e1d6e",
                "caffe926-31c8-44d4-aa10-9e3c44de86ee",
            ],
            "status": "resolved",
        },
    )
    f_payload = metal_trace["rca_finding"]
    finding_metal = post_json(
        "/rca-findings",
        {
            "anomaly_signal_id": sig_metal["id"],
            "root_cause_summary": f_payload["root_cause_summary"],
            "evidence": f_payload["evidence"],
            "suggested_fix_type": f_payload["suggested_fix_type"],
            "suggested_fix_payload": f_payload["suggested_fix_payload"],
            "confidence_score": f_payload["confidence_score"],
            "status": "proposed",
        },
    )
    print(f"        finding={finding_metal['id'][:8]} (proposed, 等主管 Accept)")

    # ----- 2) Semiconductor (Plan B technology integrated) -----
    semi_skill = json.loads((SEMI_ASSETS / "03_skill_v1.json").read_text())
    factory_semi, agent_semi, skill_semi = seed_factory_agent_skill(
        factory_name="XX 半導體封測(機密遮蔽)",
        deployment_type="on_prem",
        kpi_targets={"test_yield_pct": 98.5, "tester_uph_min": 250},
        agent_name="封測 RCA Agent",
        agent_purpose="半導體封測廠 IT/OT 事故根因分析:良率下降、Bin 突升、Tester 停機、UPH 下降",
        skill_payload=semi_skill,
    )
    print(f"[2/3] XX 半導體封測 factory={factory_semi['id'][:8]} agent={agent_semi['id'][:8]}")

    # ----- 3) Customer service (Plan A technology integrated) -----
    service_sop = SERVICE_SOP.read_text()
    service_skill_payload = {
        "prompt": (
            "# 客服維修流程助理\n\n"
            "協助系統整合公司客服中心受理、派工、處理、結案的全流程,確保 P1/P2/P3 工單依正確 SLA 推進。\n\n"
            "## Triggers\n"
            "- 客戶來電報修,請建工單\n"
            "- 工單派發給誰?\n"
            "- 工程師到場後該做什麼?\n"
            "- 維修完成,要怎麼結案?\n\n"
            "## Procedure\n\n"
            "### 1. 報修受理\n"
            "詢問客戶名稱、聯絡方式、設備型號、故障現象、緊急程度。依下列標準分級:\n"
            "- P1: 系統完全無法運作,影響營運(2 小時內到場)\n"
            "- P2: 部分功能異常但可繞行(8 小時內到場)\n"
            "- P3: 一般故障,可排程處理(48 小時內到場)\n\n"
            "### 2. 工單派發\n"
            "依故障類型對應專長工程師,考量工程師工作量,P1 優先派發。\n\n"
            "### 3. 現場處理\n"
            "工程師到場依序執行:確認故障現象 → 初步診斷 → 執行修復或更換零件 → 測試恢復狀況。\n"
            "可隨時查閱知識庫或回報技術支援。\n\n"
            "### 4. 結案紀錄\n"
            "工單需填:故障原因、處理方式、使用零件、客戶簽認。\n\n"
            "## 工具\n"
            "- query_customer_history(customer_id) — 查詢客戶歷史案件\n"
            "- query_knowledge_base(symptom) — 查知識庫類似故障\n"
            "- assign_engineer(ticket_id, priority) — 派工\n"
            "- close_ticket(ticket_id, root_cause, fix) — 結案"
        ),
        "tool_specs": [],
        "golden_test_cases": [
            {
                "id": "p1-server-down",
                "query": "客戶機房 ERP server 完全當機,影響整廠出貨",
                "expected": "判定 P1 → 2 小時內派專長工程師",
            }
        ],
        "sop_source_set_id": "set-si-customer-service",
        "generated_by_run_id": "run-si-customer-service-v1",
    }
    factory_svc, agent_svc, skill_svc = seed_factory_agent_skill(
        factory_name="SI 客服中心",
        deployment_type="private_cloud",
        kpi_targets={"p1_sla_meet_pct": 99.0, "csat_score_min": 4.5},
        agent_name="客服維修助理",
        agent_purpose="客服中心受理 / 派工 / 結案全流程助理,確保 P1/P2/P3 SLA 達標",
        skill_payload=service_skill_payload,
    )
    print(f"[3/3] SI 客服中心   factory={factory_svc['id'][:8]} agent={agent_svc['id'][:8]}")

    # ----- Summary -----
    ui = "http://localhost:3001"
    print("\n=== Ready to demo ===\n")
    print(f"打開 {ui}/factories 看到 3 個 factory:")
    print(f"  1. ACME Metals(金屬加工)— Plan C 主場域")
    print(f"     ↪ 含完整 RCA finding,可按 Accept 觸發 Self-Evolve")
    print(f"     {ui}/findings/{finding_metal['id']}")
    print(f"  2. XX 半導體封測 — Plan B 技術整合")
    print(f"     {ui}/agents/{agent_semi['id']}")
    print(f"  3. SI 客服中心   — Plan A 技術整合")
    print(f"     {ui}/agents/{agent_svc['id']}")
    print(f"\n3 個場域 / 3 個 agent / 3 套不同 skill,跑在同一個 AgentOps 平台上。")


if __name__ == "__main__":
    main()
