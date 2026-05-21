# 金屬加工 (CNC 精密加工) RCA Demo — 2026-05-20

完整 Build → Diagnose → Evolve loop,**這是 Plan C(政府計畫)金屬加工場域的正規 reference demo**。

## 時程

| 階段 | 時間 |
|---|---|
| Skill v1 mining(flows2agents,Gemini Pro)| 2 分 47 秒 |
| Trace Analyzer ReAct(autonomous trigger first attempt)| 50 秒(但沒 submit) |
| Trace Analyzer retry(max_steps=20)| **59 秒,3 FailureCases,confidence 0.85** |
| Self-Evolve(4 階段)| **4 分 10 秒,regression 3/3 PASS** |

## 場域

精密 CNC 加工廠 ACME Metals(虛構),涵蓋醫療器材、汽車零件、半導體設備零件等高精度件加工。

## SOP 內容(`01_sop_input.md`,9KB)

5 大根因原型:
1. 刀具磨損 / 崩刃
2. 熱變形 / 機台溫升
3. 夾具鬆動 / 工件定位異常
4. NC 程式 / 偏移量錯誤(換班 / 程式更新後)
5. 材料批次差異

11 個 mock tool(機台側 / 量測側 / 上游環境側),5 個歷史案例庫(INC-3001/3007/3012/3018/3025)。

## Skill v1 → v2 重點 diff(Self-Evolve 加進去的)

v2 在 Procedure Step 2 加了**「異常模式 → 優先工具」3-way 映射**:
- 多機台漸進性 → query_environment
- 換班固定量 → query_recent_changes
- 單機台新批次 → query_material_batch

完全 additive,精準命中 3 個 FailureCase。Regression PASS(3/3 resolved)。

## Plan 4 觀察:autonomous loop 部分通

- POST /anomaly-signals 確實自動觸發 Trace Analyzer ✅
- Signal 從 NEW → ANALYZING → finding 出現 ✅
- 但 PATCH /rca-findings ACCEPTED 觸發的 background self-evolve **沒寫 Skill/RegressionRun 進 DB**(已開 v0.3 ticket)
- Workaround:直接 POST /self-evolutions 同步處理 ✅

## demo asset 用途

- 政府計畫提案附件
- 主管展示「我們已經在金屬加工 domain 跑通」的證據
- v0.3 開發時的 dogfood 對象(新功能用這個 factory + agent 測試)
- v0.5 UI demo seed 來源(`scripts/seed_metal_mfg_demo_for_ui.py`)

## 2026-05-21 更新:LLM 直出中文(取代原英文版)

原 2026-05-20 跑出來的 `04_trace_analysis.json` 是 Gemini Pro 在無語言指令下
出英文。Plan 5 UI 上線後,將 trace analyzer 的 system prompt 加上「Respond in
Traditional Chinese」指令,並重跑同一組 metal-mfg traces — 取得了 LLM **直接**
產出的繁體中文 RCA finding。本檔已用該結果覆蓋。

**注意:今日 Gemini 2.5 Pro 只回 1 個 FailureCase(而非 May 20 的 3 個):**
原 May 20 在 5 個 iteration 內辨識出 3 個獨立 SOP 原型(熱變形 / 換班 / 材料批次)。
今日 May 21 重跑(signal `3ad979e4`, finding `0b831e93`)耗 16 iterations 後只
辨識出 1 個共通模式(多機台同時發生 → 查環境)。可能原因:
- Gemini Pro 模型版本可能微調
- 即使 prompt 明確要求「per-pattern 一個 case」,LLM 仍判定 3 個 trace 共享同一根因
- LLM stochasticity

**選擇接受 LLM 真實輸出而非手動翻譯**,讓 demo 反映平台真實行為。完整 3-case
英文原版仍在 git 歷史 `b0084b9` 可查。

**同步修了一個 Plan 4 bug:** `langfuse_client.search_traces` 之前讓 caller 直接
傳 `limit=500`,被 Langfuse `/v1/traces` 端點 reject(max=100)。已在
`packages/agentops_core/services/langfuse_client.py` 加 server 端 cap。
