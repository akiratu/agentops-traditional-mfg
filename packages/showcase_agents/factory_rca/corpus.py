"""Historical incident corpus for RAG.

15 past incident / maintenance records the Agent can search before/during
investigation. Mix of:
- 5 archetype-aligned cases (real similar cases the Agent should find)
- A few "edge" cases that look similar but resolve differently
- A few irrelevant cases (to verify the retriever discriminates)

Each record is a self-contained dict with the same shape.
"""
from __future__ import annotations

CORPUS: list[dict] = [
    # ─────────────────────────────────────────────────────────────
    # Probe card 壽命相關
    # ─────────────────────────────────────────────────────────────
    {
        "id": "INC-1024",
        "date": "2025-11-12",
        "title": "Tester-5 probe card 壽命末期造成 Bin 5 大量 fail",
        "severity": "P2",
        "category": "probe_card",
        "symptom": "ProductA 在 Tester-5 上 yield 一夜之間從 96% 掉到 81%，Bin 5 (open) 大量增加。其他 tester 同 lot 正常。",
        "investigation": "查 MES bin 分佈集中 Tester-5、查 probe card PC-5-018 touchdown 已達 1.91M（廠商建議上限 2M）、接觸電阻從 0.4Ω 升至 1.5Ω。",
        "root_cause": "Probe card 接近壽命末期，pin 接觸電阻過高造成假性 open。當時設定的保養門檻 2M 過於寬鬆。",
        "fix": "立即更換 probe card，過去 6 小時 Bin 5 全 retest。",
        "prevention": "Probe card 保養門檻從 2M 下修為 1.5M；新增接觸電阻 SPC 警報（7 日均值 > 1.0Ω 觸發）。",
        "tags": ["probe_card", "yield_drop", "Bin 5", "open_fail"],
    },
    {
        "id": "INC-1187",
        "date": "2026-02-08",
        "title": "PC 接觸電阻警報觸發、預防性更換 probe card",
        "severity": "P3",
        "category": "probe_card",
        "symptom": "新 SPC 規則觸發：Tester-3 上 PC-3-022 接觸電阻 7 日均值升至 1.1Ω。Yield 尚未明顯下降但趨勢警報。",
        "investigation": "查 touchdown count 1.43M（接近新門檻 1.5M），趨勢確認電阻持續上升。",
        "root_cause": "Probe card 進入壽命末期前的劣化階段。新警報規則發揮預防作用。",
        "fix": "排程下班次更換，避免事故性停線。",
        "prevention": "新規則運作正常，建議納入常規流程。",
        "tags": ["probe_card", "preventive", "SPC"],
    },
    {
        "id": "MAINT-2891",
        "date": "2026-03-22",
        "title": "FormFactor MEMS probe card 批次更換維修紀錄",
        "severity": "Routine",
        "category": "probe_card",
        "symptom": "（維修紀錄）一次更換 Tester-2/4/6 三張 probe card。",
        "investigation": "預防性更換，三張 touchdown 都在 1.45M-1.55M 之間。",
        "root_cause": "Routine maintenance。",
        "fix": "更換完成後重新校正、確認 yield 回穩。",
        "prevention": "已建立每月 probe card 狀態檢視會議。",
        "tags": ["probe_card", "maintenance", "FormFactor"],
    },

    # ─────────────────────────────────────────────────────────────
    # 韌體升版未同步 test program
    # ─────────────────────────────────────────────────────────────
    {
        "id": "INC-0987",
        "date": "2025-09-15",
        "title": "Advantest V93000 韌體 v8.4.x → v8.5.0 升版後 Vth 漂移",
        "severity": "P1",
        "category": "firmware_drift",
        "symptom": "Tester-2 韌體升版隔天，ProductB Vth correlation 與其他 tester 差 2.8%，客戶質疑。",
        "investigation": "比對 release note 第 4.3 節：『ADC sample window 縮短 8ns，舊版 test program 需調整 settling delay』。IT 端 test program 未對應更新。",
        "root_cause": "韌體升級流程缺乏 IT/OT 變更同步 — OT 升韌體未通知 IT 調 test program。",
        "fix": "Tester-2 韌體降版回 v8.4.x、重測本週批次。",
        "prevention": "建立韌體 vs test program 相依表；韌體升級流程強制 IT 簽核 gate。",
        "tags": ["firmware", "test_program", "Vth", "correlation", "ADC"],
    },
    {
        "id": "INC-1156",
        "date": "2026-01-30",
        "title": "Tester-4 韌體升版後特定 spec 失準",
        "severity": "P2",
        "category": "firmware_drift",
        "symptom": "韌體升版兩天後 Idsat correlation 差 1.8%，超過允收。",
        "investigation": "同上次案例，release note 提到 timing 改變。對照變更同步表發現 OT 工程師忘了照 SOP 通知 IT。",
        "root_cause": "變更同步流程沒被遵守，個案疏失。",
        "fix": "降版韌體並重做。",
        "prevention": "升版操作手冊強制每步驟簽名；違規記入 KPI。",
        "tags": ["firmware", "test_program", "Idsat", "change_management"],
    },
    {
        "id": "SOP-119",
        "date": "2025-12-01",
        "title": "[SOP] OT 端 tester 韌體升級標準作業流程",
        "severity": "Reference",
        "category": "firmware_drift",
        "symptom": "（SOP 文件）韌體升級前置作業檢查清單。",
        "investigation": "N/A",
        "root_cause": "N/A",
        "fix": "1. 檢查 release note 是否影響 test program 量測參數 2. 通知 IT 並取得簽核 3. 升版後做 correlation 驗證。",
        "prevention": "本 SOP 為硬性流程，每次升版前都要走完。",
        "tags": ["firmware", "SOP", "change_management"],
    },

    # ─────────────────────────────────────────────────────────────
    # 廠務壓縮機 / handler 氣壓
    # ─────────────────────────────────────────────────────────────
    {
        "id": "INC-1098",
        "date": "2025-12-18",
        "title": "B 棟主壓縮機效率下降造成多台 tester UPH 集體下滑",
        "severity": "P1",
        "category": "handler_air_pressure",
        "symptom": "下午 2 點起 B 棟 4 台 tester UPH 集體掉 25-30%，產能急單告急。",
        "investigation": "查 handler index time 變慢 → 氣壓僅 5.1 bar（標準 6.0）→ 廠務主壓縮機效率降至 78%。FDC 振動警告連續 3 天但 threshold 太鬆。",
        "root_cause": "主壓縮機老化、效率下降，輸出氣壓不足。",
        "fix": "立即切換備援壓縮機；主機停機檢修。",
        "prevention": "FDC 振動警報門檻調緊；建立月度壓縮機效率巡檢。",
        "tags": ["compressor", "air_pressure", "handler", "UPH", "facility"],
    },
    {
        "id": "INC-1245",
        "date": "2026-03-05",
        "title": "Handler 真空管路漏氣造成 pick & place 變慢",
        "severity": "P3",
        "category": "handler_air_pressure",
        "symptom": "單台 Tester-9 UPH 從 1700 掉到 1450，廠務數據看起來正常。",
        "investigation": "Handler 動作 log 顯示 pick & place 時間從 0.6s 拉到 0.85s，但廠務氣壓正常 → 縮小到 handler 本機問題 → 拆開發現真空吸盤管路有微小破損。",
        "root_cause": "Handler 端管路老化漏氣，不是廠務問題。",
        "fix": "更換真空管路。",
        "prevention": "Handler 真空管納入半年保養項目。",
        "tags": ["handler", "vacuum", "UPH", "leak"],
    },
    {
        "id": "MAINT-3104",
        "date": "2026-04-15",
        "title": "備援壓縮機啟用驗證紀錄",
        "severity": "Routine",
        "category": "handler_air_pressure",
        "symptom": "（維修紀錄）季度切換到備援壓縮機演練。",
        "investigation": "切換過程氣壓未掉、tester 不受影響。",
        "root_cause": "N/A",
        "fix": "演練完成、備援機可用。",
        "prevention": "建議季度演練。",
        "tags": ["compressor", "facility", "maintenance"],
    },

    # ─────────────────────────────────────────────────────────────
    # OT 網路 CRC / 環境
    # ─────────────────────────────────────────────────────────────
    {
        "id": "INC-1067",
        "date": "2025-10-29",
        "title": "B 棟冷氣維修後 SECS/GEM 訊號間歇斷",
        "severity": "P2",
        "category": "ot_network",
        "symptom": "冷氣 PM 隔天，3 台 tester 的 wafer map 上傳間歇性失敗。",
        "investigation": "查 OT 網路 → SW-B-14 對該 3 台 CRC error 飆升 → 機櫃濕度 72%（基準 45-55%）→ 冷氣 PM 後 humidity setpoint 未調回。",
        "root_cause": "環境濕度造成網路接頭氧化、CRC error 飆升、SECS/GEM 訊號間歇斷。",
        "fix": "調回濕度 setpoint；更換氧化接頭；重傳遺失 wafer map。",
        "prevention": "機櫃加裝獨立濕度監控；冷氣 PM 完成後 humidity setpoint 必須複查。",
        "tags": ["network", "CRC", "humidity", "SECS", "wafer_map", "facility"],
    },
    {
        "id": "INC-1212",
        "date": "2026-02-22",
        "title": "新進 CNC 機台 broadcast storm 拖垮 OT 網段",
        "severity": "P1",
        "category": "ot_network",
        "symptom": "新機台進場兩天後，整個 B 棟 OT 網路間歇性 lag、wafer map 上傳遲緩。",
        "investigation": "查 switch 流量 → 大量 broadcast 從新機台 IP 發出 → 廠商出廠時網路設定錯誤。",
        "root_cause": "新機台 PLC 網路設定錯誤造成 broadcast storm。",
        "fix": "把新機台拉到隔離 VLAN，通知廠商重設。",
        "prevention": "建立新機台入廠網路驗收清單；新設備進 OT 網路前先掃 broadcast。",
        "tags": ["network", "broadcast_storm", "VLAN", "new_equipment"],
    },
    {
        "id": "SOP-205",
        "date": "2026-01-10",
        "title": "[SOP] 冷氣維修後機房環境參數複查清單",
        "severity": "Reference",
        "category": "ot_network",
        "symptom": "（SOP 文件）",
        "investigation": "N/A",
        "root_cause": "N/A",
        "fix": "冷氣 PM 結束後須複查：溫度、濕度 setpoint、回風量、機櫃 internal humidity。",
        "prevention": "冷氣維修廠商離場前必須陪 OT 工程師走完此清單。",
        "tags": ["facility", "humidity", "SOP", "HVAC"],
    },

    # ─────────────────────────────────────────────────────────────
    # Calibration 漂移 / 標準件
    # ─────────────────────────────────────────────────────────────
    {
        "id": "INC-1284",
        "date": "2026-04-02",
        "title": "Tester-7 calibration 後 Vth 量測整體偏移",
        "severity": "P1",
        "category": "calibration_drift",
        "symptom": "年度 calibration 隔天 Vth 整體偏 1.9%，Bin 8 暴增。",
        "investigation": "Tester 本體 self-diag 正常、test program 無變更、firmware 無變更 → 鎖定 calibration → 追溯標準件 SN-201 校驗期已過 21 天。",
        "root_cause": "Calibration 使用過期標準件，等於把錯誤精度寫進機台。",
        "fix": "重做 calibration（用合格標準件）；過期校正後產品全數複測。",
        "prevention": "標準件管理系統加上 30 日到期警報；過期標準件不得借出。",
        "tags": ["calibration", "標準件", "expired", "Vth", "Bin 8"],
    },
    {
        "id": "INC-1331",
        "date": "2026-04-28",
        "title": "Calibration 標準件管理系統警報觸發",
        "severity": "P4",
        "category": "calibration_drift",
        "symptom": "新標準件管理系統 30 日警報觸發，SN-209 將於 2 週後到期。",
        "investigation": "查標準件下次 NIST 認證排程。",
        "root_cause": "正常流程，預防警報。",
        "fix": "提前送驗。",
        "prevention": "新系統運作良好，繼續維持。",
        "tags": ["calibration", "標準件", "preventive"],
    },
    {
        "id": "POSTMORTEM-2026Q1",
        "date": "2026-03-31",
        "title": "[季報] Q1 2026 校正相關事故覆盤",
        "severity": "Reference",
        "category": "calibration_drift",
        "symptom": "（季報）Q1 共 3 件 calibration drift 相關事故。",
        "investigation": "全數追溯到標準件管理流程缺口（過期 / 校驗未送 / 借用紀錄不清）。",
        "root_cause": "標準件管理流程缺乏系統化監控。",
        "fix": "Q1 末上線標準件 LIMS 整合。",
        "prevention": "預期 Q2 起此類事故歸零。",
        "tags": ["calibration", "標準件", "Q1", "postmortem"],
    },

    # ─────────────────────────────────────────────────────────────
    # 不相關案例（驗證 RAG 真的會挑相關的）
    # ─────────────────────────────────────────────────────────────
    {
        "id": "INC-1145",
        "date": "2026-01-18",
        "title": "MES 看板 dashboard 顯示異常 — 跟測試無關",
        "severity": "P3",
        "category": "irrelevant",
        "symptom": "主管看板 UPH 數字停在某個值不再更新，但實際 tester 在跑。",
        "investigation": "查發現 dashboard 後端 service 記憶體洩漏、Pod restart 後恢復。",
        "root_cause": "Dashboard service memory leak。",
        "fix": "重啟 dashboard pod；升級到修好的版本。",
        "prevention": "Dashboard 加 OOM 告警。",
        "tags": ["dashboard", "MES", "memory_leak"],
    },
    {
        "id": "INC-1078",
        "date": "2025-11-25",
        "title": "員工餐廳 POS 系統當機 — 不影響生產",
        "severity": "P4",
        "category": "irrelevant",
        "symptom": "員工餐廳 POS 機刷卡失敗。",
        "investigation": "POS 系統與廠區網路無關。",
        "root_cause": "POS 廠商雲端服務當機。",
        "fix": "等廠商恢復。",
        "prevention": "餐廳 POS 加備援。",
        "tags": ["POS", "cafeteria", "vendor"],
    },
    {
        "id": "INC-1199",
        "date": "2026-02-14",
        "title": "辦公網路斷線 — 跟 OT 網路無關",
        "severity": "P3",
        "category": "irrelevant",
        "symptom": "辦公樓員工 WiFi 連不上。",
        "investigation": "辦公網路與 OT 網路為獨立網段。",
        "root_cause": "辦公樓 AP 韌體 bug。",
        "fix": "AP 重啟、降版韌體。",
        "prevention": "辦公網路設備分批升級驗證。",
        "tags": ["WiFi", "office_network", "AP"],
    },
]


def doc_to_search_text(doc: dict) -> str:
    """Concatenate fields used for embedding."""
    parts = [
        doc.get("title", ""),
        doc.get("symptom", ""),
        doc.get("investigation", ""),
        doc.get("root_cause", ""),
        " ".join(doc.get("tags", [])),
    ]
    return "\n".join(p for p in parts if p)
