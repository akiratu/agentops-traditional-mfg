# Live Demo 流程指南

給政府計畫主管 / 場域工廠決策者 / 評審現場做 demo 用。

## 開始前 5 分鐘準備

### 確認系統在跑
```bash
curl -sf http://localhost:8000/health  # 後台
curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:3001  # 前台 (應該回 307)
```

### Reset 到乾淨狀態(每次 demo 前都跑)
```bash
cd /Users/akiratu/Downloads/claude\ code/agentops-traditional-mfg
./scripts/reset_demo.sh
```
~4 分鐘完成。會自動:
- 清掉舊資料
- Seed 3 個政府計畫場域
- 預先按 Accept 並等 Self-Evolve 產出 v2
- Promote v2 變 ACTIVE
- 印出 demo 用的 URL

### 開瀏覽器
打開 http://localhost:3001/factories — demo 從這裡開始。

---

## Demo 腳本(預估 15-20 分鐘)

### 1. 起手:三個政府計畫整合(2 分鐘)
打開 **http://localhost:3001/factories**

> 「我們做的是一個 AgentOps 平台。政府計畫承諾整合 A(客服)+ B(半導體)+ C(金屬加工)三個計畫的技術成果。
> 你現在看到的這個畫面 — 三個 factory 並列在同一個系統上。」

**指著看:**
- ACME Metals(金屬加工)— on-prem,KPI 良率 95% / 報廢 ≤2%
- XX 半導體封測 — on-prem,KPI 測試良率 98.5% / UPH ≥250
- SI 客服中心 — private cloud,KPI P1 SLA 99% / CSAT ≥4.5

### 2. 深入金屬加工 — 看 Agent 跑著什麼(2 分鐘)
**點 ACME Metals → 點 CNC RCA Agent**

> 「這是部署在金屬加工廠的 Agent,目的是『分析 CNC 精密加工的異常根因』。
> 你看右上角 — runtime 是 running,當前用的是 v2 技能。
> 下面兩欄是最近異常列表 + 技能版本演進。」

**指著看:** 右上「v2 + running」徽章 + 下面 v2 active / v1 archived 並列。

### 3. 看一個真實異常 — AI 怎麼分析(5 分鐘 · demo 殺手鐧)
**點下面「View all anomalies →」進到 Anomaly Feed**

> 「這裡是異常列表。看這個 — 三個 trace 顯示 X 軸尺寸漸進性偏移,每小時 +3μm,三台精密機都有類似現象。」

**點進去看 finding (殺手鐧頁)**

```
http://localhost:3001/findings/<finding-id>   ← reset_demo.sh 會印給你
```

> 「這是 AI 自己分析出來的內容,完全攤開來:
> - **左邊**:📓 推理筆記,四段:已查到什麼、目前推論、還需驗證、已排除。每一格都看得到 AI 用了什麼工具、找到什麼線索。
> - **右邊**:1 個失敗案例,query / expected / actual / context 都列清楚。
> - **中間**:信心 65%(這是 AI 自評,不是吹的)。
> - **右下角 sticky**:主管的決策面板。狀態已經是 ACCEPTED — 表示我們示範時主管已經按過 Accept 了。」

**講重點:**
- AI 的分析過程透明,可被質疑
- 信心分數讓決策者知道要不要相信
- 一個有失敗案例支撐的具體缺口,不是空泛的「AI 做得不好」

### 4. 看 AI 怎麼自我改善(5 分鐘)
**點上方 Skill Timeline 連結(或從 sidebar)**

```
http://localhost:3001/skills/<agent-id>   ← reset_demo.sh 會印給你
```

> 「主管按 Accept 之後,AI 在背景跑 Gemini Pro 的 4 階段 Self-Evolve:
> 1. 分析失敗模式
> 2. 提出補強 prompt
> 3. 驗證新 prompt 不會破壞舊行為
> 4. 跑回歸測試
> 
> 大約 4 分鐘後,新版 v2 skill 自動出現。」

**指著看:**
- 左邊 timeline:v2 ACTIVE(綠色邊框 + 「目前 current」標)、v1 ARCHIVED(灰色)
- 右邊 diff:左 v1、右 v2,中間 AI 加上去的補強內容上綠色

> 「右邊看到的是 v1 → v2 的差異,綠色那幾行就是 AI 為了修補剛剛那個失敗案例,自己寫進 prompt 的補強規則。完全 additive — 沒砍掉舊的,只加新的。」

### 5. 看 AI 改完真的有效(3 分鐘)
**點 sidebar 的 Regression Runs**

> 「這頁是每次 Self-Evolve 後跑的回歸測試 — 用黃金測試案例驗證新 v2 真的修好了原來的失敗,而且沒破壞其他能跑的東西。」

**點開最新一筆:**
- verdict=**PASS**
- 1/1 cases resolved

> 「verdict PASS,而且唯一一個失敗案例 status=resolved。
> 也就是說,AI 不是隨便改 prompt — 它改完還會自己跑回歸測試確認。
> 如果失敗,verdict 會是 needs_review,主管就要再看一次。」

### 6. 看其他兩個場域(各 1 分鐘)
**回到 factories 列表 → 點 XX 半導體封測 → 點封測 RCA Agent**

> 「同一套平台、不同場域。半導體封測的 Agent 看的東西不一樣 — 良率下降、Bin 突升、Tester 停機。」

**再點 SI 客服中心 → 點客服維修助理**

> 「客服場域是 Plan A 的 flow2skill 技術,從 SOP 自動生 skill 給客服中心用。
> 同一個平台、三個場域、三套不同的 skill。」

### 7. Build 階段(可選,1 分鐘,口頭講就好)
**點 SOP Upload(sidebar)**

```
http://localhost:3001/sop-upload
```

> 「最後展示一下入口:任何新場域,只要把 SOP 文件拖到這頁、按上傳 + mining,大概 2-3 分鐘 AI 就會自己挖出一個 skill v1 出來,連 3 個黃金測試案例一起。
> 我們示範時不點下去因為要等 2-3 分鐘,但流程都跑通了。」

---

## 預期主管會問的問題 + 回答

**Q: 為什麼信心只有 65%?**
> 因為 Gemini 在這次 trace 只找到 1 個共通模式(「多機台同時發生 → 沒查環境」),沒有展開到 3 個 SOP 原型。但分析內容是真實 LLM 直出的,我們選擇接受 LLM 真實判斷,不用人工美化故事。

**Q: 這 AI 一定改對嗎?**
> 不一定。所以我們設計了三道人類關卡:(1) finding 出現時你決定要不要 Accept;(2) v2 跑完你看 diff 決定要不要 Promote;(3) 回歸測試 verdict=FAIL 時系統強制標記要人工 review。

**Q: 場域工廠的線上人員怎麼操作?**
> 目前是 Developer 模式 UI(資訊密、給工程師看)。Plan 6 會做 Factory 模式 UI — 大字、觸控、「對 / 錯」按鈕。預估 2 週。

**Q: 真的部署到金屬加工廠了嗎?**
> 系統做到了 on-prem 可部署的程度,Plan 7 部署文件會把這段補完整。場域 PoC 在規劃中。

**Q: 為什麼 LLM 出來是中文?**
> Trace analyzer 的 system prompt 加了「Respond in Traditional Chinese」指令,Gemini 直接出中文。不是我們翻譯後塞進去。

**Q: 整套要花多少 LLM 成本?**
> 一輪完整 loop(Diagnose + Self-Evolve)大約 8-12 次 Gemini Pro 呼叫,單次 demo cost 估算 < NT$10。實際部署時換 on-prem Ollama 可降到 0。

---

## demo 跑壞了怎麼辦

| 狀況 | 處置 |
|---|---|
| 主管多按了一次 Accept,跑出多版 skill | 不影響 demo 故事,可繼續 |
| Self-Evolve 跑到一半要重來 | 切換到別場域填時間,或結束 demo 後 `./scripts/reset_demo.sh` |
| 某頁打開白屏 | 重新整理,或 `pkill next; cd ui && pnpm dev` |
| 後台連不上 | 看 `tail -20 /tmp/agentops-backend-gemini.log`,或 reset_demo.sh |
| Gemini API 429(限速) | 等 1 分鐘 retry,或先講多場域故事填時間 |

---

## demo 結束後

```bash
./scripts/reset_demo.sh   # 為下一場準備乾淨狀態
```

或停掉系統:
```bash
pkill -f "uvicorn agentops_core"
pkill -f "next dev"
docker compose stop
```
