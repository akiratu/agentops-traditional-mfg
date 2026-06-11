# 期中報告 demo 截圖

從本機跑著的 v0.5.0 平台直接 Playwright 拍出來的 PNG,1440×900 viewport,2x deviceScaleFactor(retina 級別,放大不糊)。

## 8 張畫面用途對照

| # | 檔名 | 報告中可用標題 / 描述 |
|---|---|---|
| 1 | `01_factories.png` | **多場域整合首頁** — 一眼看到 3 個政府計畫場域(金屬加工 / 半導體 / 客服)並列在同一平台上 |
| 2 | `02_factory_metal_detail.png` | **工廠詳情頁** — 金屬加工廠底下的 Agent 清單 + KPI 目標 + Langfuse 端點 |
| 3 | `03_agent_dashboard.png` | **Agent 儀表板** — CNC RCA Agent 的 runtime 狀態 + 最近異常 + 技能版本演進歷史 |
| 4 | `04_anomalies_feed.png` | **異常列表** — 三場域累積的 anomaly,每張卡帶 source / status / 信心徽章 |
| 5 | `05_finding_hero.png` | ⭐ **殺手鐧頁:RCA Finding 殺手鐧頁** — 4 段推理筆記 + 失敗案例 + AI 信心分數 + 決策面板(這張最能說服主管「AI 不是黑盒子」)|
| 6 | `06_skill_timeline.png` | ⭐ **Skill 版本演進** — v1 / v2 / ... 並列,右邊 GitHub PR 風格 diff,綠色就是 AI 自己加進 prompt 的補強規則 |
| 7 | `07_regression_runs.png` | **回歸測試紀錄** — 每次 Self-Evolve 後跑的 verdict + per-case 結果 |
| 8 | `08_sop_upload.png` | **Build 入口:SOP 上傳頁** — 支援 Single skill / Portfolio 兩種模式 |

## 報告中的故事順序建議

主管 / 評審看圖的閱讀順序:

```
   [01] 三場域整合  →  AgentOps 平台 = 政府計畫整合主體
        │
        ▼
   [02][03] 進金屬加工 → 部署到場域的 agent 真實存在
        │
        ▼
   [04] 異常進來
        │
        ▼
   [05] ⭐ AI 怎麼分析 → 推理過程攤開可被質疑
        │
        ▼
   [06] ⭐ AI 怎麼改善 → v1 / v2 diff 證明改了哪
        │
        ▼
   [07] 改完真的有效 → regression PASS
        │
        ▼
   [08] 從哪開始的? → Build 入口
```

## 拍圖環境

- AgentOps v0.5.0(commit `e423745` 之後)
- 後端:FastAPI + Gemini Pro
- 前端:Next.js 15 + shadcn + Tailwind v4
- 全中文(專有名詞配英文)
- 場景資料:metal-mfg-rca-2026-05-20 demo asset

## 重拍

如果要重新拍(例如做了 UI 改動之後),指令:

```bash
cd /Users/akiratu/Downloads/claude\ code/agentops-traditional-mfg/ui
node scripts/screenshot-demo.mjs
```

需要 backend / UI / Langfuse 都在跑(可用 `./scripts/reset_demo.sh` 確保乾淨資料)。
