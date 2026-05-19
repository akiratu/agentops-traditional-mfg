"""Seed semiconductor RCA traces based on rca-agent-demo's scenario archetypes.

Each trace simulates one run of an RCA agent on a real incident:
- 2 successful (agent correctly identified probe card / firmware drift root cause)
- 3 failed (agent missed obvious diagnostic steps, gave generic answers)

The failures are designed to be obviously fixable — they're all about NOT calling
specific tools that the SOP teaches. Trace Analyzer should pick this up.

Usage:
    cd /Users/akiratu/Downloads/claude\\ code/agentops-traditional-mfg
    source .venv/bin/activate
    AGENT_ID=<uuid> python scripts/seed_semiconductor_traces.py
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from langfuse import Langfuse

from agentops_core.config import get_settings


AGENT_ID = os.environ.get(
    "AGENT_ID", "073973ff-3790-4690-9595-c1f7c0ea756a"
)  # 事故 RCA Agent


def make_lf() -> Langfuse:
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        print("ERROR: LANGFUSE keys missing in .env", file=sys.stderr)
        sys.exit(1)
    return Langfuse(
        host=s.langfuse_host,
        public_key=s.langfuse_public_key,
        secret_key=s.langfuse_secret_key,
    )


def main() -> list[str]:
    lf = make_lf()
    trace_ids: list[str] = []

    base = datetime.now(tz=timezone.utc) - timedelta(days=2)

    fixtures = [
        # ============ SUCCESS 1: Probe card 壽命末期 (匹配 INC-1024) ============
        {
            "name": "rca_yield_drop_success",
            "ts": base + timedelta(hours=2),
            "input": {
                "incident": "ProductA 在 Tester-5 上 yield 從 96% 掉到 81%,Bin 5 大量增加。其他 tester 同 lot 正常。"
            },
            "output": {
                "plan": [
                    "查 MES bin 分佈,看是不是 Tester-5 集中",
                    "查 PC-5 的 touchdown count 與接觸電阻",
                    "對照 INC-1024 歷史案例",
                ],
                "tools_called": [
                    "query_mes(bin_distribution, last_4h, ProductA)",
                    "query_probe_card(PC-5-018)",
                ],
                "root_cause": "Probe card PC-5-018 接觸電阻 1.4Ω 超標,touchdown 1.91M 接近壽命末期(2M 上限)。",
                "recommended_actions": [
                    "立即更換 PC-5-018",
                    "過去 6 小時 Bin 5 全 retest",
                    "保養門檻下修為 1.5M",
                ],
                "ground_truth_match": True,
            },
            "score": 1.0,
            "scenario": "yield_drop",
        },
        # ============ SUCCESS 2: Firmware drift (匹配 INC-1284) ============
        {
            "name": "rca_firmware_drift_success",
            "ts": base + timedelta(hours=5),
            "input": {
                "incident": "Tester-4 升級 test program v3.2.1 後,ProductB 的 Bin 9 從 0.3% 升至 2.1%。"
            },
            "output": {
                "plan": [
                    "查 Tester-4 最近 test program 變更紀錄",
                    "對照升級前後 Bin 9 數據",
                    "參考 INC-1284 firmware patch 案例",
                ],
                "tools_called": [
                    "query_recent_it_changes(last_72h)",
                    "query_test_program(Tester-4)",
                    "query_mes(bin_trend, last_24h, ProductB)",
                ],
                "root_cause": "v3.2.1 firmware patch 對 ProductB 特定 die 不相容,造成 Bin 9 異常率上升。",
                "recommended_actions": ["回滾 firmware 到 v3.2.0", "QA 重新驗證 patch"],
                "ground_truth_match": True,
            },
            "score": 1.0,
            "scenario": "firmware_drift",
        },
        # ============ FAILURE 1: Probe card 場景但 agent 沒查 probe card ============
        {
            "name": "rca_yield_drop_fail_no_probecard_query",
            "ts": base + timedelta(hours=10),
            "input": {
                "incident": "ProductA 在 Tester-3 上 yield 從 95% 掉到 79%,Bin 5 暴增。其他機台正常。"
            },
            "output": {
                "plan": [
                    "查 wafer map 是不是 wafer 本身有問題",
                ],
                "tools_called": ["query_wafer_map_status(LOT-2887)"],
                "root_cause": "(資料不足)無法判定根因,建議轉送製造部進一步檢查。",
                "recommended_actions": ["建議手動排查"],
                "ground_truth_match": False,
                "missed_steps": [
                    "沒呼叫 query_probe_card 確認接觸電阻",
                    "沒對照 INC-1024 歷史案例",
                    "沒查 MES 比較其他 tester",
                ],
            },
            "score": 0.0,
            "scenario": "yield_drop",
        },
        # ============ FAILURE 2: Firmware 場景但 agent 沒查 it_changes ============
        {
            "name": "rca_firmware_drift_fail_no_change_query",
            "ts": base + timedelta(hours=15),
            "input": {
                "incident": "Tester-7 的 Bin 9 突然從 0.4% 上升到 1.8%,但其他 bin 正常,wafer 也沒換。"
            },
            "output": {
                "plan": [
                    "查 Tester-7 的硬體狀態",
                ],
                "tools_called": ["query_tester_status(Tester-7)"],
                "root_cause": "可能是 wafer 批次差異,但無法 100% 確認。",
                "recommended_actions": ["持續觀察"],
                "ground_truth_match": False,
                "missed_steps": [
                    "沒查 query_recent_it_changes 確認最近 firmware/test program 變更",
                    "沒對照 INC-1284 firmware patch 歷史案例",
                ],
            },
            "score": 0.0,
            "scenario": "firmware_drift",
        },
        # ============ FAILURE 3: Compressor 場景但 agent 沒查廠務 ============
        {
            "name": "rca_facility_fail_no_facility_query",
            "ts": base + timedelta(hours=22),
            "input": {
                "incident": "Tester-1、Tester-2、Tester-3 三台同時 UPH 下降 12%,handler 動作偶有停頓,不限 product。"
            },
            "output": {
                "plan": [
                    "查 MES 看 yield 趨勢",
                ],
                "tools_called": ["query_mes(yield_by_tester, last_4h)"],
                "root_cause": "多台 tester 同時下降,可能是系統性問題,需要進一步調查。",
                "recommended_actions": ["建議聯絡製造部"],
                "ground_truth_match": False,
                "missed_steps": [
                    "沒呼叫 query_facility 檢查壓縮空氣 / 冷卻水(SOP 4.4 明列)",
                    "沒呼叫 query_handler_metrics 看 handler 動作異常",
                    "沒對照 INC-2042 廠務歷史案例",
                ],
            },
            "score": 0.0,
            "scenario": "facility",
        },
    ]

    for fx in fixtures:
        tid = str(uuid.uuid4())
        lf.trace(
            id=tid,
            name=fx["name"],
            user_id=AGENT_ID,
            input=fx["input"],
            output=fx["output"],
            metadata={
                "agent_id": AGENT_ID,
                "skill_version": 1,
                "scenario": fx["scenario"],
                "synthetic": True,
            },
            timestamp=fx["ts"],
        )
        lf.score(
            trace_id=tid,
            name="rca_accuracy",
            value=fx["score"],
            comment=("ground truth match" if fx["score"] >= 0.5 else "miss"),
        )
        trace_ids.append(tid)
        marker = "✅" if fx["score"] >= 0.5 else "❌"
        print(f"  {marker} {fx['name']}: trace_id={tid[:8]}...")

    lf.flush()
    time.sleep(1)

    print(f"\n{len(trace_ids)} traces seeded for AGENT_ID={AGENT_ID}")
    print("\nFailed trace IDs (for AnomalySignal):")
    for tid in trace_ids[2:]:
        print(f"  {tid}")

    return trace_ids


if __name__ == "__main__":
    main()
