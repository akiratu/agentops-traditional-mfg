# RCA Agent Demo — Design Spec

**Date**: 2026-05-16
**Audience**: 智慧製造廠主管 (executives)
**Goal**: 3 分鐘內讓主管理解「AI Agent 怎麼自動跨 IT/OT 查事故根因」

---

## 1. Product Overview

A single-page Streamlit web app demonstrating an autonomous Root Cause Analysis (RCA) agent for a smart manufacturing facility. The agent receives an incident, then iteratively calls mock tools across IT and OT systems to identify the root cause, and presents recommended actions.

The demo emphasizes **cross-domain investigation** — IT teams and OT teams traditionally argue over whose problem an incident is. The agent shows AI bridging that gap.

---

## 2. Scope

### In Scope
- Streamlit web UI (single page, `streamlit run app.py`)
- 2 pre-built incident scenarios with fixture data
- Real Gemini API integration (`google-genai` SDK, model `gemini-2.0-flash-exp`)
- 10 mock tools (5 IT + 5 OT), each backed by per-scenario JSON fixtures
- ReAct-style agent loop with streaming output
- Visual timeline showing each tool call tagged with 🖥️ IT or 🔧 OT
- Conclusion card: Business Impact → Root Cause → Recommended Actions
- Sidebar Gemini API key input (with `.env` support)

### Out of Scope (YAGNI)
- Real monitoring system integration
- Multi-tenant / auth
- Historical incident database
- Cloud deployment (local-only)
- Customizable scenarios via UI (scenarios live in JSON files)

---

## 3. Scenarios

### Scenario 1: Yield Drop — Probe Card 接近壽命
**Business framing on card**:
> 🎯 **Yield 從 95% 掉到 78%**
> 某客戶 product 大量 Bin 5 (open) fail，retest 成本暴增，
> RMA 風險升高。每小時影響營收約 NT$ 1.2M。

**Expected investigation path** (Agent is free to deviate, but fixtures are designed to lead here):
1. 🖥️ `query_mes("bin_distribution", "last_4h", filter="product_A")` → Bin 5 spike 集中在 Tester #7
2. 🖥️ `query_mes("yield_by_tester", "last_4h")` → 同 lot 在 Tester #3 正常 (排除 wafer 本身問題)
3. 🔧 `query_probe_card("PC-7-042")` → touchdown count 1.8M / 接觸電阻趨勢上升
4. 🔧 `query_tester_status("Tester-7")` → 設備本體正常
5. 🖥️ `query_recent_it_changes()` → 保養門檻設 2M，無近期變更

**Root cause**: Probe card 接近壽命末期，pin 接觸電阻變大造成假性 open。

**Recommended actions**:
1. 立即換 Tester #7 probe card，過去 4 小時 Bin 5 全部 retest
2. 保養門檻從 2M 改 1.5M
3. 加上接觸電阻 SPC 警報

---

### Scenario 2: Tester Correlation Drift — 韌體升級沒同步 Test Program
**Business framing on card**:
> 🔬 **同批 wafer 在兩台 tester 結果差 3%**
> 客戶質疑數據可信度、要求重測整批，
> 商譽風險、付款流程被卡。

**Expected investigation path**:
1. 🖥️ `query_correlation("Tester-5", "Tester-8", spec="Vth")` → Vth 差 3.2%，遠超允收
2. 🖥️ `query_test_program("Tester-5")` 與 `query_test_program("Tester-8")` → 兩台同版本 v3.2.1
3. 🔧 `query_tester_status("Tester-8")` → 上週做過 calibration
4. 🔧 `query_tester_status("Tester-8")` (firmware field) → 上週韌體升級 v8.4.7 → v8.5.2
5. 🖥️ `query_recent_it_changes()` → release note 顯示新韌體改了 ADC sample timing，但 test program 未對應調整

**Root cause**: OT 升韌體未通知 IT 調 test program → 量測時序錯位。

**Recommended actions**:
1. Tester #8 韌體降版 + 重測本週數據
2. 建立韌體 / test program 版本綁定表
3. 韌體升級流程加 IT 簽核 gate

---

## 4. Architecture

```
┌──────────────────────────────────────────────────┐
│  Streamlit UI (app.py)                            │
│  - Sidebar: API key, scenario picker, "Go" button │
│  - Main: Timeline (streaming) + Conclusion card   │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│  Agent Loop (agent.py)                            │
│  - Builds system prompt with persona & toolset    │
│  - Streams Gemini response                        │
│  - Parses function calls → dispatches to tools    │
│  - Loops until model returns final answer or 8x   │
└────────┬──────────────────────┬──────────────────┘
         │                      │
         ▼                      ▼
┌────────────────┐    ┌─────────────────────────┐
│ Gemini API     │    │ Mock Tools (tools.py)   │
│ google-genai   │    │ Reads scenarios/*.json  │
│ gemini-2.0-... │    │ 5 IT + 5 OT functions   │
└────────────────┘    └─────────────────────────┘
```

### File Layout
```
rca_demo/
├── app.py                       # Streamlit UI
├── agent.py                     # Gemini agent loop
├── tools.py                     # 10 mock tools + function declarations
├── scenarios/
│   ├── scenario_1_yield_drop.json
│   └── scenario_2_correlation_drift.json
├── prompts/
│   └── system_prompt.txt        # Persona + investigation guidelines
├── requirements.txt
├── .env.example
└── README.md                    # Brief run instructions
```

---

## 5. Component Specs

### 5.1 Streamlit UI (`app.py`)

**Layout** (using `st.columns([1, 3])` for sidebar-like effect inside main area, plus actual `st.sidebar` for config):

- **Sidebar**
  - API key input (`st.text_input(type="password")`, persists in `st.session_state`)
  - Model selector (default `gemini-2.0-flash-exp`)
  - Max iterations slider (default 8)

- **Main area**
  - Header: "🔬 智慧製造廠 — AI 根因分析 Agent (Demo)"
  - 2 scenario cards (side-by-side `st.columns(2)`) with business framing; clicking "▶ 派 AI 去查" sets `st.session_state.active_scenario` and triggers run
  - Once running: clear cards, show:
    - **Investigation Timeline** (`st.container` that updates as stream arrives)
      - Each entry rendered as expandable card with: step number, agent's natural-language thought, tool icon (🖥️/🔧) + tool name + args, tool result (collapsed by default)
    - **Conclusion Card** (rendered after loop ends)
      - 🔴 業務影響 (red banner)
      - 🔍 根本原因 (blue card)
      - ✅ 建議行動 (green checklist)

**Streaming UX**: use `st.empty()` placeholders that get rewritten on each agent step. Tool calls appear immediately; tool results appear with a brief "thinking..." spinner during the synchronous tool dispatch.

### 5.2 Agent Loop (`agent.py`)

Function signature:
```python
def run_agent(
    scenario_id: str,
    api_key: str,
    model: str,
    max_iterations: int,
    on_event: Callable[[Event], None],
) -> Conclusion
```

`Event` is a tagged union:
- `ThoughtEvent(text)` — model's natural language between tool calls
- `ToolCallEvent(tool_name, domain, args)` — about to call a tool
- `ToolResultEvent(tool_name, result_summary)` — tool returned
- `ConclusionEvent(business_impact, root_cause, actions)` — final structured output

**Loop**:
1. Initialize Gemini client with function-calling tools
2. Send system prompt + scenario intro as first user message
3. While iterations < max:
   a. Stream model response, emit `ThoughtEvent`s as text chunks arrive
   b. If model emits function call → emit `ToolCallEvent`, dispatch to `tools.py`, emit `ToolResultEvent`, append result to history
   c. If model emits final answer with structured conclusion → parse, emit `ConclusionEvent`, break
4. If max iterations hit without conclusion → emit a fallback `ConclusionEvent` saying "需更多資料"

**Structured conclusion**: instruct the model to terminate by calling a special pseudo-tool `submit_conclusion(business_impact, root_cause, actions)`. This is cleaner than parsing free-form text.

### 5.3 Mock Tools (`tools.py`)

10 functions, each:
- Accepts typed args matching the Gemini function declaration
- Looks up the active scenario's fixture data
- Returns a dict (JSON-serializable)

Fixtures are keyed by `(tool_name, args_hash)` so the same tool with different args can return different data (e.g., `query_mes("yield_by_tester")` vs `query_mes("bin_distribution")`).

When the agent calls a tool with args not in the fixture, return a generic "no relevant data" response — this is fine, the agent will try another tool.

### 5.4 System Prompt

Sets up the agent as a senior SRE who is fluent in both IT and OT, knows the testing floor, and **must translate findings into business language** for the executive viewing the demo. Critically: every thought emitted must be **in 繁體中文, executive-friendly, no jargon dumps**.

Example: instead of "Querying MES for Bin 5 distribution over last 4h" → "我先看一下哪幾台機台的 fail 變多".

---

## 6. Data Contracts

### Scenario JSON shape
```json
{
  "id": "scenario_1_yield_drop",
  "title": "Yield 從 95% 掉到 78%",
  "business_summary": "某客戶 product 大量 Bin 5 fail...",
  "hourly_revenue_impact": "NT$ 1.2M",
  "incident_message": "(seed message Agent receives)",
  "fixtures": {
    "query_mes": {
      "bin_distribution|last_4h|product_A": { ... },
      "yield_by_tester|last_4h": { ... }
    },
    "query_probe_card": {
      "PC-7-042": { ... }
    }
  },
  "expected_root_cause_keywords": ["probe card", "壽命", "touchdown"]
}
```

The `expected_root_cause_keywords` field is for an optional sanity check / future eval — not enforced at runtime.

---

## 7. Error Handling

- **No API key**: UI shows a friendly inline error in the sidebar; scenario buttons disabled until provided
- **Gemini API error**: catch, show as red banner in timeline, allow retry without resetting state
- **Tool call with unknown scenario fixture**: return `{"status": "no_data", "hint": "try a different query"}` — agent will adapt
- **Max iterations reached**: render a "需更多資料" conclusion card with what the agent learned so far

We do NOT add retries, exponential backoff, or sophisticated error recovery — this is a demo.

---

## 8. Testing Strategy

Manual demo verification only:
1. `streamlit run app.py` starts cleanly
2. Both scenarios run end-to-end with real Gemini API
3. Agent reaches the intended root cause in both cases (verified by reading the timeline)
4. Tool calls in timeline correctly tag IT vs OT
5. Conclusion card renders with all 3 sections

No unit tests — the agent's exact path is non-deterministic and fixtures are designed to guide it. We verify by running.

---

## 9. Dependencies

```
streamlit>=1.30
google-genai>=0.3
python-dotenv>=1.0
```

Python 3.13 (existing `.venv`).

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Gemini decides to skip a tool we expected → conclusion is weak | Fixtures are designed so multiple paths lead to the same root cause; system prompt nudges toward thorough investigation |
| Streaming render flickers / janky | Use `st.empty()` per step, only update the active step's placeholder |
| API rate limit during live demo | Use Flash model (high quota); show a "thinking..." spinner so a slow first token doesn't feel broken |
| Main misinterprets Chinese root-cause text | System prompt forces structured `submit_conclusion` tool call with fixed fields |

---

## 11. Definition of Done

- [ ] Both scenarios run end-to-end with real Gemini API
- [ ] Timeline shows IT/OT tags correctly
- [ ] Conclusion card has business impact, root cause, actions — all in 繁體中文
- [ ] README explains how to set API key and run
- [ ] App starts with `streamlit run app.py` and no extra setup beyond `pip install -r requirements.txt`
