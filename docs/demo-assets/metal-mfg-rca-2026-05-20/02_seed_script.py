"""Seed CNC precision machining RCA traces.

5 synthetic traces simulating a "CNC RCA Agent" deployed at a 精密加工廠:
- 2 successful (agent correctly matched archetype + queried tools + cited INC)
- 3 failed (agent missed obvious diagnostic steps from the SOP, gave generic answers)

Usage:
    cd /Users/akiratu/Downloads/claude\\ code/agentops-traditional-mfg
    source .venv/bin/activate
    AGENT_ID=<uuid> python scripts/seed_metal_traces.py
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from langfuse import Langfuse

from agentops_core.config import get_settings


AGENT_ID = os.environ.get("AGENT_ID", "")  # set via env


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
    if not AGENT_ID:
        print("ERROR: set AGENT_ID env var before running", file=sys.stderr)
        sys.exit(1)

    lf = make_lf()
    trace_ids: list[str] = []
    base = datetime.now(tz=timezone.utc) - timedelta(days=2)

    fixtures = [
        # =========================================================
        # SUCCESS 1: 刀具磨損 → 對映 INC-3001
        # =========================================================
        {
            "name": "rca_tool_wear_success",
            "ts": base + timedelta(hours=2),
            "input": {
                "incident": "醫療精密件,M-04 機台,T-08 球刀加工的件,尺寸從 ±3μm 偏移到 +12μm,良率從 98% 掉到 71%"
            },
            "output": {
                "plan": [
                    "查 T-08 刀具壽命狀態(對映「刀具磨損」原型)",
                    "查 M-04 主軸負載趨勢看磨損證據",
                    "對照 INC-3001 歷史案例",
                ],
                "tools_called": [
                    "query_tool_life(T-08)",
                    "query_spindle_load(M-04, last_4h)",
                    "query_inspection_log(batch=L-2026-0520-001)",
                ],
                "root_cause": "T-08 球刀累計加工 4.5 小時,VB 磨損超過 0.15mm,主軸負載 7 件均值 +18%,造成正偏移。對映 INC-3001 模式。",
                "recommended_actions": [
                    "立即更換 T-08",
                    "過去 2 小時件 CMM 重檢",
                    "刀具壽命警報下修到 3.5 小時",
                ],
                "ground_truth_match": True,
            },
            "score": 1.0,
            "scenario": "tool_wear",
        },
        # =========================================================
        # SUCCESS 2: 夾具鬆動 → 對映 INC-3007
        # =========================================================
        {
            "name": "rca_fixture_loose_success",
            "ts": base + timedelta(hours=5),
            "input": {
                "incident": "M-07 機台早上 8:30 上機後第一批件全部 X 軸 -0.08mm 偏移,後續批件正常"
            },
            "output": {
                "plan": [
                    "查 F-02 夾具拆裝紀錄(對映「夾具鬆動」原型)",
                    "查最近 NC 程式有沒有改動排除程式因素",
                    "對照 INC-3007 歷史案例",
                ],
                "tools_called": [
                    "query_fixture_log(F-02)",
                    "query_recent_changes(M-07, last_24h)",
                ],
                "root_cause": "F-02 夾具今早 8:00 拆洗保養後 8:30 上機,沒有標準件試切校正紀錄,定位銷與機台座標偏差。對映 INC-3007。",
                "recommended_actions": [
                    "首批件全部召回重工",
                    "夾具回校位後重新試切",
                    "更新夾具拆裝 SOP 強制校位紀錄",
                ],
                "ground_truth_match": True,
            },
            "score": 1.0,
            "scenario": "fixture_loose",
        },
        # =========================================================
        # FAILURE 1: 熱變形場景但 agent 沒查環境 / 機台溫度
        # =========================================================
        {
            "name": "rca_thermal_drift_fail_no_env_query",
            "ts": base + timedelta(hours=12),
            "input": {
                "incident": "M-04 下午 3 點開始 X 軸尺寸漸進性偏移,每小時 +3μm,3 台精密機都有類似現象"
            },
            "output": {
                "plan": [
                    "查 M-04 是不是刀具有問題",
                ],
                "tools_called": ["query_tool_life(T-08)"],
                "root_cause": "(資料不足)無法判定根因,建議轉送製造部進一步檢查。",
                "recommended_actions": ["建議手動排查"],
                "ground_truth_match": False,
                "missed_steps": [
                    "沒呼叫 query_environment 查廠房溫度(SOP 4.2 明列為熱變形必查)",
                    "沒呼叫 query_cnc_status 查主軸溫度",
                    "沒注意「3 台機同時受影響」= 廠務 / 環境問題的關鍵訊號",
                    "沒對照 INC-3018 夏季空調故障案例",
                ],
            },
            "score": 0.0,
            "scenario": "thermal_drift",
        },
        # =========================================================
        # FAILURE 2: NC 程式異動場景但 agent 沒查 recent_changes
        # =========================================================
        {
            "name": "rca_nc_program_fail_no_changes_query",
            "ts": base + timedelta(hours=18),
            "input": {
                "incident": "M-07 早班接班後發現整批件 Z 軸 -0.015mm 偏移,Ra 也劣化,但夜班沒回報任何異常"
            },
            "output": {
                "plan": [
                    "查 M-07 機台狀態",
                ],
                "tools_called": ["query_cnc_status(M-07, last_4h)"],
                "root_cause": "機台狀態正常,可能是材料批次差異,需要進一步抽檢。",
                "recommended_actions": ["建議聯絡材料部抽檢"],
                "ground_truth_match": False,
                "missed_steps": [
                    "沒呼叫 query_recent_changes 查最近 NC / offset 變更(SOP 4.4 明列為換班場景必查)",
                    "沒注意「換班後突然偏移同樣的量」= NC 程式 / 偏移量問題的關鍵訊號",
                    "沒對照 INC-3025 夜班改 offset 沒登記案例",
                    "沒查 query_nc_program 看程式版本",
                ],
            },
            "score": 0.0,
            "scenario": "nc_program",
        },
        # =========================================================
        # FAILURE 3: 材料批次差異場景但 agent 沒查 material_batch
        # =========================================================
        {
            "name": "rca_material_batch_fail_no_batch_query",
            "ts": base + timedelta(hours=22),
            "input": {
                "incident": "M-04 加工同一個 NC 程式同把刀具,但今天的件 Ra 從 0.8 變 1.6,切削音變高,昨天件正常"
            },
            "output": {
                "plan": [
                    "查 M-04 機台",
                ],
                "tools_called": ["query_cnc_status(M-04, last_4h)"],
                "root_cause": "可能是機台問題,需要找維修保養。",
                "recommended_actions": ["建議報修"],
                "ground_truth_match": False,
                "missed_steps": [
                    "沒呼叫 query_material_batch 查材料批次(SOP 4.5 明列為「同程式同刀但結果不同」場景必查)",
                    "沒注意「同程式同刀但 Ra 跳變 + 切削音變化」= 材料硬度差異的關鍵訊號",
                    "沒對照 INC-3012 新供應商鋼材硬度差異案例",
                    "沒查 query_inspection_log 比對前後批次",
                ],
            },
            "score": 0.0,
            "scenario": "material_batch",
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
