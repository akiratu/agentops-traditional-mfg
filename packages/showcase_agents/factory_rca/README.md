# 🔬 智慧製造廠 — AI 根因分析 (RCA) Agent Demo

給工廠主管看的 AI Agent demo。模擬事故發生時，AI 自動跨 **IT**（MES、生產程式、看板）與 **OT**（產線設備、PLC、廠務）兩個系統，搭配 **歷史事故 RAG** + **rolling context compression**，找出根因並提出建議。

## 🎯 主要功能

| 功能 | 說明 |
|------|------|
| **🎲 隨機事故產生器** | 5 個根因原型（probe card 壽命、firmware drift、廠務壓縮機、OT 網路 CRC、calibration drift），每次隨機生成不同事故。**真實根因藏起來，Agent 真的要查才知道**。 |
| **📋 Agent 自擬計畫** | 開始調查前，Agent 自己呼叫 `submit_plan` 提出 3-5 步調查策略，邊查邊打勾 (`mark_plan_step_done`)。 |
| **🔎 RAG 歷史案例檢索** | 事故進來時自動檢索 18 篇歷史 corpus，找出 top-3 相似案例（embedding-based, gemini-embedding-001），注入 Agent context。 |
| **🗜️ 上下文壓縮** | Hermes-style「drop middle + insert summary」：舊 tool 結果折進 LLM 即時生成的結構化筆記本，省 30-60% token，準確度不受影響。 |
| **📔 Agent 工作筆記本** | Agent 邊查邊整理 4 段結構化摘要（已查到什麼 / 目前推論 / 還需驗證 / 已排除），既給人看也給 Agent 自己參考。 |
| **🎭 答案揭曉** | 結論出來後，自動比對真實根因與 Agent 找到的根因，標 ✅ 命中 / ⚠️ 部分 / ❌ 沒中。 |

## 🚀 快速開始

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 設定 Gemini API Key（任選一）
export GEMINI_API_KEY=your-key-here
# 或複製 .env.example → .env 填入
# 或啟動後在 UI sidebar 直接貼

# 3. 啟動
streamlit run app.py
```

預設 model `gemini-2.5-flash`，可在 sidebar 切換到 `gemini-2.5-pro`、`gemini-2.0-flash` 或 Gemma 系列。

## 📁 檔案結構

```
rca_demo/
├── app.py              # Streamlit UI (情境卡 + 計畫 + Timeline + 筆記本 + RAG + 結論)
├── agent.py            # Gemini agent loop + 壓縮 + 筆記本生成
├── tools.py            # 10 個 mock tools (5 IT + 5 OT) + function declarations
├── generator.py        # 隨機事故產生器 (5 個根因原型)
├── rag.py              # Embedding + cosine similarity retriever
├── corpus.py           # 18 篇歷史事故 / 維修 fixture
├── scenarios/          # 2 個固定情境 (yield drop, correlation drift)
├── prompts/
│   └── system_prompt.txt
├── docs/
│   └── design-spec.md  # 完整設計文件
└── requirements.txt
```

## 🎬 主管 Demo 建議流程

1. **講開場**：「待會丟一個 AI 從來沒看過的事故給它」
2. **點「🎲 隨機事故」**
3. **第一個亮點**：5 秒內 Agent 翻歷史 corpus 找出 3 件相似案例（RAG）
4. **第二個亮點**：Agent 自己擬出 3-5 步計畫，邊查邊打勾
5. **第三個亮點**：左下角筆記本即時更新「目前推論 / 還需驗證」
6. **第四個亮點**：Timeline 上每個 tool call 標 🖥️ IT 或 🔧 OT，主管看到 AI 在跨域
7. **第五個亮點**：metrics 條顯示「省 token 50%+」
8. **揭曉**：結論卡片 + 答案揭曉面板「真實根因 vs Agent 找到的」
9. **破除 scripted 疑慮**：連跑 3 次，每次根因不同；切換 model 推理風格不同

## 🏗️ 架構亮點（給工程主管的版本）

```
事故進來
    ↓
🔎 RAG 檢索 (top 3 相似歷史案例) ─────┐
    ↓                                  │
🤖 Agent 擬計畫 (submit_plan)         │ 全部注入
    ↓                                  │ Agent context
🔧 ReAct loop: 呼叫 IT/OT tools       │
    ├─ 每輪 emit token stats          │
    └─ 舊 tool 結果折進筆記本 ────────┤
        (rule pre-pass + LLM summarize)│
    ↓                                  │
🗒️ 筆記本不斷更新 (4 段結構化)        │
    ↓                                  │
🎯 submit_conclusion ←────────────────┘
    ↓
🎭 揭曉：keyword matching 命中率
```

## 🔌 接真實系統需要做什麼

詳見 `docs/design-spec.md`。簡言之：
- **RAG corpus**：把 `corpus.py` 換成接 Jira / Confluence / 內部 wiki
- **10 個 tools**：每個寫 connector 接 MES、SECS/GEM、BMS、ChangeMgmt 等
- **其餘**（Agent loop、壓縮、筆記本、RAG infra）**完全不用動**

## 📝 加新情境

複製 `scenarios/scenario_1_yield_drop.json` 改成你的情境即可，新檔自動出現在 UI 上。Tool fixture 的 key 是 `arg=value|arg=value`（順序不拘），找不到 match 時回傳 `default`。

加新的根因原型則在 `generator.py` 加一個 `gen_xxx(rng)` 函式並註冊到 `ARCHETYPES` dict。
