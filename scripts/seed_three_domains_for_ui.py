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
SERVICE_ASSETS = REPO / "docs/demo-assets/customer-service-2026-05-21"


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
    # Load the customer-service skill from a real flows2agents mining run.
    # The run_id points to existing storage at data/skills/f2a-1f9d7cceac7b/
    # servicecenterflow/ so Self-Evolve can load the IR and produce v2 when
    # the user accepts the corresponding finding.
    service_skill = json.loads((SERVICE_ASSETS / "03_skill_v1.json").read_text())
    factory_svc, agent_svc, skill_svc = seed_factory_agent_skill(
        factory_name="SI 客服中心",
        deployment_type="private_cloud",
        kpi_targets={"p1_sla_meet_pct": 99.0, "csat_score_min": 4.5},
        agent_name="客服維修助理",
        agent_purpose="客服中心受理 / 派工 / 結案全流程助理,確保 P1/P2/P3 SLA 達標",
        skill_payload=service_skill,
    )
    print(f"[3/3] SI 客服中心   factory={factory_svc['id'][:8]} agent={agent_svc['id'][:8]}")

    # ----- Demo drama: add anomaly + finding for semi & customer service too,
    # so all 3 domains have a story (not just "deployed, idle"). -----
    semi_sig = post_json(
        "/anomaly-signals",
        {
            "agent_id": agent_semi["id"],
            "source_type": "metric_drift",
            "related_trace_refs": ["semi-trace-yield-drop-001"],
            "status": "resolved",
        },
    )
    finding_semi = post_json(
        "/rca-findings",
        {
            "anomaly_signal_id": semi_sig["id"],
            "root_cause_summary": (
                "技能缺口:Tester 機台 #3 良率突降至 78%(原 96%),Agent 只查了"
                " MES 良率報表,沒呼叫 `query_tester_maintenance_log` 對照最近"
                " 的 Tester 保養紀錄。SOP 5.3 指出 Bin 4 突升 + 單機台事件應"
                "優先查 Tester 內部狀態,而非廠務或材料。"
            ),
            "evidence": {
                "notebook": (
                    "## 🔍 已查到什麼\n"
                    "- [fetch_trace_detail] Tester-3 良率自昨日 22:00 突降至 78%。\n"
                    "- [fetch_trace_detail] Bin 4 比例從 0.5% 拉升到 14%,屬於"
                    " Probe Card 接觸不良的典型 fingerprint。\n"
                    "- [fetch_skill_detail] Skill prompt 描述了通用 RCA 流程,"
                    "但沒明列 SOP 5.3 的「Bin 4 突升 + 單機台」對應規則。\n\n"
                    "## 💡 目前推論\n"
                    "Agent 收到良率告警後直奔 MES 報表,沒有依「單機台 vs 全廠」"
                    "二分流程先呼叫 `query_tester_maintenance_log` 看 Tester 內部"
                    "保養 / Probe Card 更換時序。\n\n"
                    "## ❓ 還需驗證\n"
                    "(已足夠,可提交 failure case)\n\n"
                    "## 🚫 已排除\n"
                    "- 廠務問題:其他 Tester 都正常,單機台事件,排除。\n"
                    "- 材料批次:同批 Wafer 在其他 Tester 良率正常,排除。"
                ),
                "failure_case_ids": ["bin4-spike-missed-tester-maintenance"],
                "plan_steps_completed": 4,
                "total_iterations": 7,
                "termination": "terminated_by_submit",
            },
            "suggested_fix_type": "supplement_sop",
            "suggested_fix_payload": {
                "failure_cases": [
                    {
                        "id": "bin4-spike-missed-tester-maintenance",
                        "query": (
                            "Tester-3 從昨晚 22:00 開始良率掉到 78%,Bin 4 突"
                            "升到 14%,其他 Tester 都正常"
                        ),
                        "expected_outcome": (
                            "Agent 應辨識「單機台 + Bin 4 突升」是 Probe Card "
                            "接觸不良典型徵兆,依 SOP 5.3 立即呼叫"
                            " `query_tester_maintenance_log` 查最近的 Probe "
                            "Card 更換 / 機台保養紀錄。"
                        ),
                        "actual_outcome": (
                            "Agent 只呼叫了 `query_mes_yield_report` 確認良率"
                            "確實掉了,然後就建議「請廠務檢查」。沒有切到"
                            "「單機台優先查 Tester 內部」這條 SOP 5.3 規則。"
                        ),
                        "context": "trace_id=semi-trace-yield-drop-001; skill_version=1",
                    }
                ]
            },
            "confidence_score": 0.78,
            "status": "proposed",
        },
    )
    print(f"        ↪ semi finding={finding_semi['id'][:8]} (proposed)")

    svc_sig = post_json(
        "/anomaly-signals",
        {
            "agent_id": agent_svc["id"],
            "source_type": "human_flag",
            "related_trace_refs": ["svc-trace-p1-escalation-fail-042"],
            "status": "resolved",
        },
    )
    finding_svc = post_json(
        "/rca-findings",
        {
            "anomaly_signal_id": svc_sig["id"],
            "root_cause_summary": (
                "技能缺口:客戶報修 ERP server 當機(P1),客服助理判定為 P2,"
                "派工 SLA 從 2 小時拉長到 8 小時,造成出貨延誤。SOP 1 明列"
                "「系統完全無法運作 / 影響營運」即為 P1,但 skill prompt 沒"
                "明確示範這個對應。"
            ),
            "evidence": {
                "notebook": (
                    "## 🔍 已查到什麼\n"
                    "- [fetch_trace_detail] 客戶來電原話: 「ERP server 整個"
                    "當掉,出貨單沒辦法開」。\n"
                    "- [fetch_trace_detail] Agent 在判定階段選擇 P2(部分功能"
                    "異常但可繞行),理由為「客戶可手動開單」。\n"
                    "- [fetch_skill_detail] Skill prompt 對 P1/P2/P3 描述清楚"
                    "但沒列舉「ERP / MES / 出貨」這類核心系統屬於 P1 的範例。\n\n"
                    "## 💡 目前推論\n"
                    "Agent 太字面解讀「可繞行」三個字,沒考慮業務影響。SOP 1 的"
                    "P1 定義其實是「影響營運」,任何擋住出貨的當機都該是 P1。\n\n"
                    "## ❓ 還需驗證\n"
                    "(已足夠)\n\n"
                    "## 🚫 已排除\n"
                    "- 工程師資源不足:當下有空閒專長工程師可派,排除。"
                ),
                "failure_case_ids": ["p1-misclassified-as-p2"],
                "plan_steps_completed": 3,
                "total_iterations": 5,
                "termination": "terminated_by_submit",
            },
            "suggested_fix_type": "supplement_sop",
            "suggested_fix_payload": {
                "failure_cases": [
                    {
                        "id": "p1-misclassified-as-p2",
                        "query": "ERP server 整個當掉,出貨單沒辦法開",
                        "expected_outcome": (
                            "Agent 應辨識「ERP / MES / 出貨」為核心營運系統,"
                            "依 SOP 1 的「影響營運」判準直接歸 P1(2 小時 SLA)。"
                        ),
                        "actual_outcome": (
                            "Agent 字面解讀「可手動繞行」就降級為 P2(8 小時"
                            " SLA),造成出貨延誤。"
                        ),
                        "context": "trace_id=svc-trace-p1-escalation-fail-042; skill_version=1",
                    }
                ]
            },
            "confidence_score": 0.82,
            "status": "proposed",
        },
    )
    print(f"        ↪ service finding={finding_svc['id'][:8]} (proposed)")

    # ----- Summary -----
    ui = "http://localhost:3001"
    print("\n=== Ready to demo ===\n")
    print(f"打開 {ui}/factories 看到 3 個 factory,各有自己的 finding 故事:")
    print(f"  1. ACME Metals(金屬加工)— Plan C 主場域")
    print(f"     finding: {ui}/findings/{finding_metal['id']}")
    print(f"  2. XX 半導體封測   — Plan B 技術整合")
    print(f"     finding: {ui}/findings/{finding_semi['id']}")
    print(f"  3. SI 客服中心     — Plan A 技術整合")
    print(f"     finding: {ui}/findings/{finding_svc['id']}")
    print(f"\n3 個場域 / 3 個 agent / 3 套不同 skill / 3 個正在等主管 Accept 的 finding。")


if __name__ == "__main__":
    main()
