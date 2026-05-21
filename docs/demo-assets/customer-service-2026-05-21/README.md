# 客服維修 RCA Demo — 2026-05-21

Plan A(flow2skill)技術整合進 AgentOps 平台後,在 v0.5 demo 中
代表「客服場域」的 reference skill v1。

## 來源

從 `packages/flows2agents/tests/fixtures/service-portfolio/mini-sop.md` 透過
flows2agents.mining_pipeline 使用 Gemini 2.5 Pro 真實挖出來的 v1。
產出的 storage 在 `data/skills/f2a-1f9d7cceac7b/servicecenterflow/`,
存的 IR + SKILL.md + eval-report.json 都還在,可作為 Self-Evolve 的基礎。

## 03_skill_v1.json 結構

| 欄位 | 內容 |
|---|---|
| prompt | SKILL.md 全文(包含 Procedure 5 步) |
| tool_specs | flows2agents 推斷的 tool 簽名 |
| golden_test_cases | 3 個從 SOP 推導的測試 |
| sop_source_set_id | 對應 storage 的 set ID |
| generated_by_run_id | 對應 storage 路徑,Self-Evolve 需要 |

## 跟另兩個場域的差異

- 半導體:從 docs/demo-assets/semiconductor-rca-2026-05-19/ 載入(2026-05-19 同樣方式產出)
- 金屬加工:從 docs/demo-assets/metal-mfg-rca-2026-05-20/ 載入(2026-05-20 產出)

三個場域的 skill 都是「**真的**透過 flows2agents 挖出來的」, Accept finding 後
Self-Evolve 可以正常跑、產出 v2 skill。
