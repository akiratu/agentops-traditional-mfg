# 智慧製造廠 — IC 測試廠根因分析 (RCA) 作業規範

## 1. 適用範圍

本規範適用於半導體封裝測試廠的事故 / 異常根因分析作業。涵蓋:
- Yield 突降事件(>10 個百分點 / 4 小時窗)
- Bin 集中異常(單一 Bin 比例 > 30%)
- Tester 機台異常停機
- Probe card 接觸品質劣化
- Handler / facility / OT 網路異常
- 跨機台、跨產品的良率相關性問題

## 2. 角色與職責

| 角色 | 職責 |
|---|---|
| 線上工程師 (SE) | 第一線發現異常、執行初步診斷 |
| RCA Agent / 系統 | 跨 IT / OT 自動診斷,提交調查計畫與結論 |
| 製造主管 | 審核 agent 結論、決定停機/重測/換料 |
| 維修工程師 | 執行 probe card / handler 更換、firmware 升級 |
| QA 工程師 | 歷史事故知識庫維護、SPC 規則調整 |

## 3. 標準調查流程

### Phase 1:擬定調查計畫 (Plan)

收到事故通報後,**第一個動作是擬定 3-5 步調查計畫**,而非直接查資料。每步必須包含:
- **假設**:用主管聽得懂的話描述要驗證什麼
- **動作**:預計要查的系統與資料

### Phase 2:跨域診斷執行

執行計畫,使用以下工具:

#### IT 側工具(MES、看板、生產程式)
- `query_mes(metric, window, filter)` — bin 分佈、yield 趨勢、tester 比較
- `query_test_program(tester_id)` — test program 版本、最近變更
- `query_correlation(metric_a, metric_b)` — 機台間關聯性
- `query_wafer_map_status(lot_id)` — wafer map / 製造端狀態
- `query_recent_it_changes(window)` — IT 系統最近改動

#### OT 側工具(設備、感測器、廠務)
- `query_tester_status(tester_id)` — 機台溫度、狀態
- `query_handler_metrics(tester_id)` — handler 動作、機械臂狀態
- `query_probe_card(card_id)` — touchdown count、接觸電阻趨勢
- `query_facility(window)` — 廠務電力、壓縮空氣、冷卻水
- `query_ot_network(window)` — PLC / SECS-GEM 網路狀態

### Phase 3:歷史案例對照 (RAG)

調查時必須**明確引用歷史案例**,展示「用古鑑今」:

範例:「步驟 1:先看是不是 Tester 集中 fail(**參考 INC-1024,當年 Probe card 壽命末期造成 Bin 5 大量 fail**)」

不要只看完不講出來。

### Phase 4:強因果證據後下結論

呼叫 `submit_conclusion`,提供:
- root_cause:技術性根因
- business_impact:對良率 / 營收 / 客戶的衝擊
- recommended_actions:立即處置 + 預防措施

## 4. 5 大根因原型

下列為廠內歷史最常見的事故根因原型,Agent 應該優先檢驗:

### 4.1 Probe card 壽命末期
- **症狀**:特定 Tester yield 在數小時內掉 10-20%,Bin 5 (open) 集中
- **典型徵兆**:touchdown count > 1.5M、接觸電阻 7 日均值 > 1.0Ω
- **必查項**:`query_probe_card(card_id)`、`query_mes("bin_distribution", "last_4h")`
- **參考案例**:INC-1024(2025-11-12 PC-5-018)、INC-1187(2026-02-08 預防性)

### 4.2 Firmware drift (test program 版本飄移)
- **症狀**:同 wafer 在不同 Tester yield 不一致;test program 變更後特定 bin 異常
- **必查項**:`query_test_program(tester_id)`、`query_recent_it_changes("last_72h")`
- **參考案例**:INC-1284(2025-12-03 firmware patch 後 Bin 9 異常)

### 4.3 Calibration drift (校正偏移)
- **症狀**:單一 Tester 上特定 product 量測值整體偏移、Bin 邊界附近異常
- **必查項**:`query_tester_status` + 確認最近 calibration 紀錄
- **參考案例**:INC-1098

### 4.4 Compressor / facility 異常(廠務)
- **症狀**:多 Tester 同時 UPH 下降、handler 動作異常、不限特定 product
- **必查項**:`query_facility("last_24h")`、`query_handler_metrics`
- **參考案例**:INC-2042(壓縮機冷卻塔異常)

### 4.5 OT 網路 CRC / SECS-GEM 通訊異常
- **症狀**:tester ↔ MES 資料不一致、bin 上傳延遲、UPH 統計缺失
- **必查項**:`query_ot_network("last_4h")`、`query_mes("data_integrity")`

## 5. 歷史案例庫(節錄)

### INC-1024 (2025-11-12, P2):Tester-5 probe card 壽命末期造成 Bin 5 大量 fail
- 症狀:ProductA 在 Tester-5 上 yield 一夜之間從 96% 掉到 81%
- 調查:MES bin 分佈集中 Tester-5、probe card PC-5-018 touchdown 已達 1.91M、接觸電阻從 0.4Ω 升至 1.5Ω
- 根因:Probe card 接近壽命末期,pin 接觸電阻過高造成假性 open
- 處置:立即更換 + 過去 6 小時 Bin 5 全 retest
- 預防:保養門檻從 2M 下修為 1.5M;新增接觸電阻 SPC 警報

### INC-1187 (2026-02-08, P3):PC 接觸電阻警報觸發、預防性更換
- 症狀:新 SPC 規則觸發:Tester-3 PC-3-022 接觸電阻 7 日均值升至 1.1Ω
- 根因:Probe card 進入壽命末期前的劣化階段
- 處置:排程下班次更換

### INC-1284 (2025-12-03, P2):Test program 升級後 Bin 9 異常率上升
- 症狀:Tester-4 升級 test program v3.2.1 之後,Bin 9 (functional fail) 異常率從 0.3% 升至 2.1%
- 根因:firmware 升級引入的 patch 對 ProductB 特定 die 不相容
- 處置:回滾 firmware 版本

### INC-2042 (2025-10-15, P1):廠務壓縮機冷卻塔異常
- 症狀:3 個 Tester 同時 UPH 下降 15%,handler 動作出現停頓
- 根因:冷卻塔泵浦故障導致壓縮空氣含水量上升
- 處置:啟動備援冷卻塔 + 維修主泵

## 6. SLA 與通報規範

| 事故等級 | 首次回應 | 結案目標 | 通報對象 |
|---|---|---|---|
| P1 系統全面停機 | 15 分鐘內 | 4 小時內 | 廠長、製造主管、IT 主管 |
| P2 部分機台異常 | 30 分鐘內 | 8 小時內 | 製造主管 |
| P3 趨勢警報 | 2 小時內 | 24 小時內 | 製造主管 |

## 7. 結論範本

```
業務衝擊:
  - 受影響產品線 / 機台
  - 預估 yield 損失 (%)
  - 預估時間 (小時)
  - 預估營收衝擊 (NTD)

根因:
  - 一句話技術描述
  - 證據鏈(從 MES / OT / probe card 等資料推論)

立即處置:
  - 具體動作 + 負責人 + 完成時間

預防措施:
  - SPC 規則 / 保養門檻調整
  - 知識庫補登
  - 教育訓練
```

## 8. Agent 行為守則

1. 全程繁體中文,使用主管聽得懂的話
2. 不堆 jargon,但要保留關鍵技術詞彙(probe card、touchdown count、Bin 5 等)
3. 呼叫工具前必須說明「為什麼要查這個」
4. 收到結果後必須說「看到什麼、推論什麼」
5. 找到強因果證據才下結論,不要憑空猜測
6. 引用歷史案例 ID,展示推理透明度
