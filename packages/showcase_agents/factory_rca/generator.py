"""Random RCA scenario generator.

Each call produces a fresh, internally-consistent incident with one of 5 root
cause archetypes. The agent does not see the ground truth; it must investigate
to find it.

Output shape matches the static scenario JSON files used by tools.py, plus a
`ground_truth` block consumed only by the reveal panel (NOT exposed to the
agent).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

TESTERS = ["Tester-3", "Tester-5", "Tester-7", "Tester-8", "Tester-12"]
PRODUCTS = ["ProductA", "ProductB", "ProductC", "ProductD"]


def _other_testers(broken: str, n: int = 3) -> list[str]:
    pool = [t for t in TESTERS if t != broken]
    return random.sample(pool, k=min(n, len(pool)))


def _lot_id(rng: random.Random) -> str:
    return f"LOT-{rng.choice(['A', 'B', 'C', 'D'])}{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"


def _money(rng: random.Random, low: int, high: int) -> str:
    n = rng.randint(low, high)
    return f"NT$ {n:,} / 小時"


# ---------------------------------------------------------------------------
# Archetype 1 — probe card 接近壽命
# ---------------------------------------------------------------------------
def gen_probe_card_eol(rng: random.Random) -> dict[str, Any]:
    broken = rng.choice(TESTERS)
    others = _other_testers(broken)
    product = rng.choice(PRODUCTS)
    card_id = f"PC-{broken.split('-')[1]}-{rng.randint(10, 99):03d}"
    other_card_ids = {t: f"PC-{t.split('-')[1]}-{rng.randint(10, 99):03d}" for t in others}
    yield_normal = rng.randint(94, 97)
    yield_drop = rng.randint(15, 22)
    yield_now = yield_normal - yield_drop
    touchdown = rng.randint(1750000, 1920000)
    resistance_now = round(rng.uniform(1.25, 1.65), 2)
    lot = _lot_id(rng)

    trend = []
    base = 0.55
    for _ in range(7):
        trend.append(round(base, 2))
        base += rng.uniform(0.10, 0.20)
    trend[-1] = resistance_now

    fixtures = {
        "query_mes": {
            "default": {"status": "no_data", "hint": "請指定 metric 與 timerange"},
            f"metric=bin_distribution|timerange=last_4h|filter={product}": {
                "summary": f"過去 4 小時 {product} bin 分佈",
                "data": {
                    "Bin 1 (Pass)": f"{yield_now}.0% (-{yield_drop}.0pp vs 7 日均值)",
                    "Bin 5 (Open)": f"{yield_drop + 1}.5% (+{yield_drop}pp ⚠️ 暴增)",
                    "Bin 7 (Speed)": "2.1%",
                    "Bin 8 (Leakage)": "1.4%",
                },
                "note": "Bin 5 (Open) 暴增是 yield 下降主因",
            },
            "metric=yield_by_tester|timerange=last_4h": {
                "summary": f"過去 4 小時各 Tester yield ({product})",
                "data": {
                    **{t: f"{rng.randint(93, 96)}.{rng.randint(0, 9)}% (正常)" for t in others},
                    broken: f"{yield_now}.{rng.randint(0, 9)}% ⚠️ 異常偏低",
                },
                "note": f"問題集中在 {broken}。同一 lot 在其他 tester 結果正常 → 排除 wafer 問題",
            },
            "metric=bin5_by_tester|timerange=last_4h": {
                "summary": "Bin 5 fail 在各 Tester 的分佈",
                "data": {
                    **{t: f"0.{rng.randint(7, 12)}%" for t in others},
                    broken: f"{yield_drop + rng.randint(15, 20)}.{rng.randint(0, 9)}% ⚠️",
                },
            },
            f"metric=lot_history|timerange=last_24h|filter={lot}": {
                "summary": f"{lot} 在各 tester 的測試紀錄",
                "data": f"此 lot 部分 wafer 走 {broken} (yield 偏低)，部分走其他 tester (正常)。確認 wafer 本身無異常。",
            },
        },
        "query_probe_card": {
            "default": {
                "status": "no_data",
                "hint": "請指定 card_id (例如先用 query_tester_status 取得目前裝在 tester 上的 probe card)",
            },
            f"card_id={card_id}": {
                "summary": f"Probe card {card_id} ({broken} 目前使用中)",
                "data": {
                    "model": "FormFactor-MEMS-256",
                    "touchdown_count": f"{touchdown:,} / 2,000,000 ({touchdown/20000:.0f}%)",
                    "installed_date": "2025-09-12",
                    "last_clean": "2026-05-17 22:00",
                    "contact_resistance_avg": f"{resistance_now} Ω (基準 0.4 Ω，⚠️ {resistance_now/0.4:.1f}x)",
                    "contact_resistance_trend_48h": trend,
                    "note": "接觸電阻持續上升、touchdown 接近壽命門檻 (2M)。pin 磨損造成假性 open (Bin 5)",
                },
            },
            **{
                f"card_id={cid}": {
                    "summary": f"Probe card {cid} ({t} 使用中)",
                    "data": {
                        "touchdown_count": f"{rng.randint(300000, 900000):,} / 2,000,000",
                        "contact_resistance_avg": f"0.{rng.randint(40, 55)} Ω (正常)",
                        "note": "狀態良好，對照組",
                    },
                }
                for t, cid in other_card_ids.items()
            },
        },
        "query_tester_status": {
            "default": {"status": "no_data", "hint": "請指定 tester_id"},
            f"tester_id={broken}": {
                "summary": f"{broken} 狀態",
                "data": {
                    "model": "Advantest V93000",
                    "status": "Running",
                    "firmware": f"v8.4.{rng.randint(5, 9)} (無近期變更)",
                    "test_program": f"TP-{product}-v3.2.1",
                    "last_calibration": "2026-04-29 (正常週期)",
                    "probe_card_installed": card_id,
                    "handler": "Cohu Diamondx (正常)",
                    "self_diagnostic": "Pass",
                    "note": "Tester 本體無異常",
                },
            },
            **{
                f"tester_id={t}": {
                    "summary": f"{t} 狀態",
                    "data": {
                        "status": "Running",
                        "probe_card_installed": cid,
                        "self_diagnostic": "Pass",
                    },
                }
                for t, cid in other_card_ids.items()
            },
        },
        "query_handler_metrics": {
            "default": {"status": "no_data"},
            f"tester_id={broken}": {
                "summary": f"{broken} handler 動作指標",
                "data": {
                    "index_time_avg": "1.2s (正常)",
                    "air_pressure": "6.1 bar (正常)",
                    "vacuum": "正常",
                    "note": "Handler 無異常",
                },
            },
        },
        "query_facility": {"default": {"summary": "廠務", "data": "B 棟環境正常"}},
        "query_ot_network": {"default": {"summary": "OT 網路", "data": "SECS/GEM 連線穩定，CRC error 正常"}},
        "query_test_program": {
            "default": {"status": "no_data"},
            f"tester_id={broken}": {
                "summary": f"{broken} test program",
                "data": {
                    "name": f"TP-{product}-v3.2.1",
                    "last_modified": "2026-03-12",
                    "note": "近期無變更",
                },
            },
        },
        "query_correlation": {
            "default": {
                "summary": "Correlation",
                "data": "近 7 日各 tester 對規格的 correlation 在允收內 (差異為 yield 數量，非規格漂移)",
            },
        },
        "query_wafer_map_status": {"default": {"summary": "Wafer map", "data": "上傳成功率 99.8% (正常)"}},
        "query_recent_it_changes": {
            "default": {
                "summary": "近 14 日 IT 變更紀錄",
                "data": {
                    "MES 升版": "2026-05-04 (兩週前，與此事故無關)",
                    "保養門檻設定": "Probe card touchdown 警示門檻設於 2,000,000，無近期變更",
                    "test program": f"TP-{product} 自 v3.2.1 (2026-03-12) 起無更新",
                    "note": "保養門檻 2M 為廠商建議上限，業界實務常在 1.5M 即更換",
                },
            },
        },
    }

    return {
        "id": f"random_probe_card_eol_{rng.randint(1000, 9999)}",
        "title": f"Yield 從 {yield_normal}% 掉到 {yield_now}%",
        "icon": "🎯",
        "business_summary": f"{product} 過去 4 小時 yield 大幅下滑，Bin 5 (open) 暴增，retest 成本暴增，RMA 風險升高。",
        "hourly_revenue_impact": _money(rng, 900_000, 1_500_000),
        "incident_message": (
            f"事故通報：今天 2026-05-18 下午 3 點，產品 {product} 過去 4 小時 yield 從 {yield_normal}% "
            f"掉到 {yield_now}%，Bin 5 (open) fail 大量增加。批次 {lot} 受影響。"
            f"客戶已注意到，請查根因並提出建議。"
        ),
        "fixtures": fixtures,
        "ground_truth": {
            "archetype_id": "probe_card_eol",
            "archetype_name": "Probe card 接近壽命末期",
            "summary": f"{broken} 上的 probe card {card_id} 接近壽命末期 (touchdown {touchdown:,} / 上限 2M)，pin 接觸電阻已升至 {resistance_now}Ω (基準 0.4Ω)，造成 Bin 5 假性 open。",
            "key_facts": {
                "broken_tester": broken,
                "broken_card": card_id,
                "touchdown": touchdown,
                "resistance": resistance_now,
            },
            "expected_keywords": ["probe card", "壽命", "touchdown", "接觸電阻", broken, card_id],
        },
    }


# ---------------------------------------------------------------------------
# Archetype 2 — 韌體升版未同步 test program
# ---------------------------------------------------------------------------
def gen_firmware_drift(rng: random.Random) -> dict[str, Any]:
    tester_old = rng.choice(TESTERS)
    tester_new = rng.choice([t for t in TESTERS if t != tester_old])
    product = rng.choice(PRODUCTS)
    spec = rng.choice(["Vth", "Vt0", "Vmin"])
    diff_pct = round(rng.uniform(2.8, 3.8), 1)
    upgrade_date = "2026-05-11"
    lot = _lot_id(rng)
    old_fw = f"v8.{rng.randint(3, 4)}.{rng.randint(5, 9)}"
    new_fw = f"v8.5.{rng.randint(0, 4)}"
    tp_version = f"v2.{rng.randint(6, 8)}.{rng.randint(0, 5)}"

    fixtures = {
        "query_mes": {
            "default": {"status": "no_data"},
            "metric=yield_by_tester|timerange=last_24h": {
                "summary": f"近 24h 各 tester yield ({product})",
                "data": {
                    tester_old: f"94.{rng.randint(0, 8)}%",
                    tester_new: f"91.{rng.randint(0, 5)}% (略低)",
                },
                "note": "Yield 差異不大，重點是規格量測值差異",
            },
            f"metric=lot_history|timerange=last_24h|filter={lot}": {
                "summary": f"{lot} 測試紀錄",
                "data": f"此 lot 部分 wafer 走 {tester_old}，部分走 {tester_new}，wafer 間應一致。",
            },
        },
        "query_correlation": {
            "default": {"status": "no_data", "hint": "請指定 tester_a, tester_b, spec"},
            f"tester_a={tester_old}|tester_b={tester_new}|spec={spec}": {
                "summary": f"{tester_old} vs {tester_new} {spec} correlation (近 7 日)",
                "data": {
                    f"{tester_old} 平均 {spec}": "0.682 V",
                    f"{tester_new} 平均 {spec}": "0.660 V",
                    "差異": f"{diff_pct}% ⚠️ (允收 ±1%)",
                    "趨勢": f"差異自 {upgrade_date} 起出現並持續放大",
                    "註": f"{upgrade_date} 之前 correlation 在 0.3% 以內 (正常)",
                },
            },
            f"tester_a={tester_old}|tester_b={tester_new}|spec=Idsat": {
                "summary": f"{tester_old} vs {tester_new} Idsat correlation",
                "data": {"差異": "0.4% (允收內)"},
                "note": "差異只在電壓相關量測 → 暗示量測 timing 相關",
            },
        },
        "query_test_program": {
            "default": {"status": "no_data"},
            f"tester_id={tester_old}": {
                "summary": f"{tester_old} test program",
                "data": {
                    "name": f"TP-{product}-{tp_version}",
                    "last_modified": "2026-02-14",
                    "compatible_firmware": "≥ v8.4.0",
                },
            },
            f"tester_id={tester_new}": {
                "summary": f"{tester_new} test program",
                "data": {
                    "name": f"TP-{product}-{tp_version}",
                    "last_modified": "2026-02-14",
                    "compatible_firmware": "≥ v8.4.0",
                    "note": "與另一台同版本",
                },
            },
        },
        "query_tester_status": {
            "default": {"status": "no_data"},
            f"tester_id={tester_old}": {
                "summary": f"{tester_old} 狀態",
                "data": {
                    "firmware": old_fw,
                    "last_firmware_update": "2025-11-20 (半年前)",
                    "last_calibration": "2026-04-30",
                    "self_diagnostic": "Pass",
                },
            },
            f"tester_id={tester_new}": {
                "summary": f"{tester_new} 狀態",
                "data": {
                    "firmware": f"{new_fw} ⚠️ ({upgrade_date} 升版)",
                    "last_firmware_update": f"{upgrade_date} (一週前)",
                    "last_calibration": f"{upgrade_date} (韌體升版後校正)",
                    "self_diagnostic": "Pass",
                    "note": "韌體升級時間點與 correlation 異常出現時間點一致",
                },
            },
        },
        "query_probe_card": {"default": {"summary": "Probe card", "data": "兩台 tester 的 probe card 狀態正常"}},
        "query_handler_metrics": {"default": {"summary": "Handler", "data": "正常"}},
        "query_facility": {"default": {"summary": "廠務", "data": "正常"}},
        "query_ot_network": {"default": {"summary": "OT 網路", "data": "正常"}},
        "query_wafer_map_status": {"default": {"summary": "Wafer map", "data": "上傳成功率 100%"}},
        "query_recent_it_changes": {
            "default": {
                "summary": "近 14 日變更",
                "data": {
                    f"{tester_new} 韌體升級": f"{upgrade_date} 由 OT 工程師執行 {old_fw} → {new_fw} (release note: 改善 ADC 取樣 timing)",
                    f"{tester_new} calibration": f"{upgrade_date} 韌體升級後執行",
                    "Test program": f"TP-{product}-{tp_version} 自 2026-02-14 起無變更",
                    "release_note_key_point": f"{new_fw} release note 第 4.3 節：『ADC sample window 縮短 8ns，部分舊版 test program 需調整 settling delay』",
                    "IT 端應變": "❌ 此次韌體升級未通知 IT，test program 未對應更新 settling delay",
                },
                "note": "這是經典的 IT/OT 變更管理斷層",
            },
        },
    }

    return {
        "id": f"random_firmware_drift_{rng.randint(1000, 9999)}",
        "title": f"同批 wafer 在兩台 tester {spec} 結果差 {diff_pct}%",
        "icon": "🔬",
        "business_summary": f"{tester_old} 與 {tester_new} 對同一批 wafer 量測差 {diff_pct}%，客戶要求重測整批、暫停出貨。",
        "hourly_revenue_impact": "出貨被卡、付款流程暫停",
        "incident_message": (
            f"事故通報：今天 2026-05-18，客戶 QA 反映同一批 wafer ({lot}) 在 {tester_old} "
            f"與 {tester_new} 之間 {spec} 量測結果差 {diff_pct}%，超出允收範圍 (±1%)。"
            f"客戶要求釐清原因並暫停整批出貨。"
        ),
        "fixtures": fixtures,
        "ground_truth": {
            "archetype_id": "firmware_drift",
            "archetype_name": "韌體升版未同步 test program",
            "summary": f"OT 工程師於 {upgrade_date} 將 {tester_new} 韌體升版 ({old_fw}→{new_fw})，新韌體縮短 ADC sample window，但 test program 未對應調整 settling delay，導致 {spec} 出現系統性偏移。",
            "key_facts": {
                "old_tester": tester_old,
                "new_tester": tester_new,
                "spec": spec,
                "diff_pct": diff_pct,
            },
            "expected_keywords": ["韌體", "firmware", "test program", "ADC", "timing", tester_new],
        },
    }


# ---------------------------------------------------------------------------
# Archetype 3 — Handler 氣壓不足（廠務壓縮機老化）
# ---------------------------------------------------------------------------
def gen_handler_air_pressure(rng: random.Random) -> dict[str, Any]:
    broken = rng.choice(TESTERS)
    others = _other_testers(broken)
    product = rng.choice(PRODUCTS)
    uph_normal = rng.choice([1600, 1700, 1800, 1900])
    uph_now = uph_normal - rng.randint(400, 600)
    air_normal = 6.0
    air_now = round(rng.uniform(4.8, 5.4), 1)
    pick_normal = 0.6
    pick_now = round(rng.uniform(0.95, 1.15), 2)

    fixtures = {
        "query_mes": {
            "default": {"status": "no_data"},
            "metric=yield_by_tester|timerange=last_4h": {
                "summary": f"過去 4 小時 yield ({product})",
                "data": {
                    **{t: f"{rng.randint(93, 96)}.{rng.randint(0, 9)}% (正常)" for t in others},
                    broken: f"{rng.randint(93, 96)}.{rng.randint(0, 9)}% (正常)",
                },
                "note": "Yield 沒掉，是 throughput 掉",
            },
            "metric=throughput_by_tester|timerange=last_4h": {
                "summary": "各 tester UPH (units per hour)",
                "data": {
                    **{t: f"{rng.randint(1500, 1850)} UPH (正常)" for t in others},
                    broken: f"{uph_now} UPH ⚠️ (比平常 {uph_normal} 少約 {uph_normal-uph_now})",
                },
                "note": f"{broken} UPH 明顯下滑，產能受影響",
            },
            "metric=test_time_breakdown|timerange=last_4h": {
                "summary": f"{broken} 測試時間分解",
                "data": {
                    "actual_test_time": "1.8s (正常)",
                    "handler_index_time": f"2.4s ⚠️ (正常應 1.2s)",
                    "結論": "test 本身沒變慢，是 handler 動作變慢",
                },
            },
        },
        "query_handler_metrics": {
            "default": {"status": "no_data", "hint": "請指定 tester_id"},
            f"tester_id={broken}": {
                "summary": f"{broken} handler 動作指標",
                "data": {
                    "index_time_avg": "2.4s ⚠️ (基準 1.2s)",
                    "pick_place_time": f"{pick_now}s ⚠️ (基準 {pick_normal}s)",
                    "air_pressure": f"{air_now} bar ⚠️ (基準 {air_normal} bar)",
                    "vacuum": "marginal",
                    "note": "氣壓不足造成真空吸取變慢、pick & place 拉長",
                },
            },
            **{
                f"tester_id={t}": {
                    "summary": f"{t} handler",
                    "data": {
                        "index_time_avg": "1.2s (正常)",
                        "air_pressure": "6.0 bar (正常)",
                    },
                }
                for t in others
            },
        },
        "query_facility": {
            "default": {"status": "no_data", "hint": "請指定 item (例如 compressor_main / cleanroom_B)"},
            "item=compressor_main": {
                "summary": "主壓縮機狀態",
                "data": {
                    "output_pressure": f"{air_now} bar (應 6.0)",
                    "efficiency": f"{rng.randint(72, 82)}% (基準 95%)",
                    "vibration": "異常偏高 (FDC 已連續 3 天有 warning，但 threshold 設太鬆未觸發 alarm)",
                    "runtime_hours": f"{rng.randint(18000, 22000)} h (接近大修週期 20,000h)",
                    "note": "效率下降、振動異常，建議立即切換到備援機",
                },
            },
            "item=cleanroom_B": {"summary": "B 棟無塵室", "data": "溫濕度正常"},
        },
        "query_tester_status": {
            "default": {"status": "no_data"},
            f"tester_id={broken}": {
                "summary": f"{broken} 狀態",
                "data": {"status": "Running", "self_diagnostic": "Pass", "note": "tester 本體正常"},
            },
        },
        "query_probe_card": {"default": {"summary": "Probe card", "data": "狀態正常"}},
        "query_test_program": {"default": {"summary": "Test program", "data": "近期無變更"}},
        "query_correlation": {"default": {"summary": "Correlation", "data": "正常"}},
        "query_wafer_map_status": {"default": {"summary": "Wafer map", "data": "上傳正常"}},
        "query_ot_network": {"default": {"summary": "OT 網路", "data": "正常"}},
        "query_recent_it_changes": {
            "default": {
                "summary": "近 14 日變更",
                "data": {
                    "Test program": "無變更",
                    "FDC 警報": "壓縮機振動 FDC warning 已連續 3 天，但 alarm threshold 設太鬆，未升級為 alarm",
                },
            },
        },
    }

    return {
        "id": f"random_handler_air_{rng.randint(1000, 9999)}",
        "title": f"{broken} UPH 從 {uph_normal} 掉到 {uph_now}",
        "icon": "🐌",
        "business_summary": f"{broken} 產能下降 ~30%，急單交期受影響，整線 capacity 卡住。",
        "hourly_revenue_impact": _money(rng, 500_000, 900_000),
        "incident_message": (
            f"事故通報：今天 2026-05-18，{broken} 測試 {product} 的 UPH 從平常 {uph_normal} "
            f"掉到 {uph_now}，現場 operator 反映機台動作好像變慢。整線 capacity 受影響。請查根因。"
        ),
        "fixtures": fixtures,
        "ground_truth": {
            "archetype_id": "handler_air_pressure",
            "archetype_name": "廠務壓縮機老化 → handler 氣壓不足",
            "summary": f"主壓縮機效率下降至 ~78%，輸出氣壓僅 {air_now} bar (應 6.0)，{broken} handler 真空吸取變慢，pick & place 時間從 {pick_normal}s 拉長到 {pick_now}s，UPH 從 {uph_normal} 掉到 {uph_now}。FDC 雖有 warning 但 threshold 太鬆未觸發 alarm。",
            "key_facts": {
                "broken_tester": broken,
                "uph_normal": uph_normal,
                "uph_now": uph_now,
                "air_pressure": air_now,
            },
            "expected_keywords": ["壓縮機", "氣壓", "compressor", "handler", "廠務", "UPH"],
        },
    }


# ---------------------------------------------------------------------------
# Archetype 4 — OT 網路 CRC error (switch / 濕度)
# ---------------------------------------------------------------------------
def gen_ot_network_crc(rng: random.Random) -> dict[str, Any]:
    broken = rng.choice(TESTERS)
    others = _other_testers(broken)
    product = rng.choice(PRODUCTS)
    fail_pct = rng.randint(12, 22)
    crc_error_rate = round(rng.uniform(0.8, 2.4), 2)
    humidity = rng.randint(67, 78)

    fixtures = {
        "query_wafer_map_status": {
            "default": {
                "summary": "Wafer map 上傳狀態",
                "data": {
                    "近 6 小時整體成功率": f"{100 - fail_pct}% ⚠️ (基準 99.9%)",
                    "失敗來源集中": broken,
                    "失敗總數": rng.randint(80, 200),
                    "note": "上傳失敗會導致 wafer map 缺漏、出貨被卡",
                },
            },
        },
        "query_ot_network": {
            "default": {"status": "no_data", "hint": "請指定 segment 或 switch ID"},
            f"segment=floor_B": {
                "summary": "B 棟 OT 網路",
                "data": {
                    "整體流量": "正常",
                    "異常 switch": f"SW-B-12 (連接 {broken})",
                    "SW-B-12 CRC error rate": f"{crc_error_rate}% ⚠️ (基準 < 0.01%)",
                    "port_link_flap": "近 6h 觀察到 23 次 link down/up",
                    "SECS/GEM 連線": f"{broken} 連線間歇性 timeout",
                    "note": "CRC error 飆高通常是實體層問題 (接頭氧化、線材破損、電磁干擾)",
                },
            },
        },
        "query_facility": {
            "default": {"status": "no_data"},
            "item=cleanroom_B": {
                "summary": "B 棟無塵室",
                "data": {
                    "temperature": "22.1°C (正常)",
                    "humidity": f"{humidity}% ⚠️ (基準 45-55%)",
                    "particle_count": "正常",
                    "note": "近期冷氣 PM 後濕度控制異常",
                },
            },
            "item=hvac_zone_B": {
                "summary": "B 棟冷氣系統",
                "data": {
                    "last_maintenance": "2026-05-15 (3 天前)",
                    "current_status": "運轉中但濕度控制 setpoint 未恢復",
                    "note": "PM 後 setpoint 沒調回，導致濕度偏高",
                },
            },
        },
        "query_tester_status": {
            "default": {"status": "no_data"},
            f"tester_id={broken}": {
                "summary": f"{broken} 狀態",
                "data": {
                    "status": "Running",
                    "self_diagnostic": "Pass",
                    "GEM_connection": "Intermittent disconnects",
                    "note": "tester 本身運轉正常，但對外通訊不穩",
                },
            },
        },
        "query_mes": {
            "default": {"status": "no_data"},
            "metric=yield_by_tester|timerange=last_6h": {
                "summary": "各 tester yield",
                "data": {**{t: "正常" for t in others}, broken: "正常 (但 wafer map 部分缺失)"},
            },
        },
        "query_handler_metrics": {"default": {"summary": "Handler", "data": "正常"}},
        "query_probe_card": {"default": {"summary": "Probe card", "data": "正常"}},
        "query_test_program": {"default": {"summary": "Test program", "data": "正常"}},
        "query_correlation": {"default": {"summary": "Correlation", "data": "正常"}},
        "query_recent_it_changes": {
            "default": {
                "summary": "近 14 日變更",
                "data": {
                    "冷氣 PM": "2026-05-15 由廠務執行年度 PM，恢復後 humidity setpoint 未調回",
                    "其他": "無相關 IT 變更",
                },
            },
        },
    }

    return {
        "id": f"random_ot_network_{rng.randint(1000, 9999)}",
        "title": f"客戶要的 wafer map 缺失 {fail_pct}%",
        "icon": "📡",
        "business_summary": f"{broken} 的 wafer map 上傳近 6 小時失敗 {fail_pct}%，出貨被卡、客戶 audit 風險。",
        "hourly_revenue_impact": "出貨延誤、客戶 audit 風險",
        "incident_message": (
            f"事故通報：今天 2026-05-18，客戶反映 {product} 出貨附帶的 wafer map 有缺檔，"
            f"系統顯示近 6 小時 {fail_pct}% 上傳失敗。出貨被卡，請查根因。"
        ),
        "fixtures": fixtures,
        "ground_truth": {
            "archetype_id": "ot_network_crc",
            "archetype_name": "OT 網路 CRC error (環境濕度造成接頭氧化)",
            "summary": f"B 棟冷氣 PM 後濕度 setpoint 未調回，無塵室濕度升至 {humidity}%，造成 SW-B-12 對 {broken} 的網路接頭氧化，CRC error rate 飆至 {crc_error_rate}%，SECS/GEM 訊號間歇性斷線，wafer map 上傳失敗。",
            "key_facts": {
                "broken_tester": broken,
                "fail_pct": fail_pct,
                "humidity": humidity,
            },
            "expected_keywords": ["CRC", "濕度", "humidity", "switch", "接頭", "SECS", "冷氣"],
        },
    }


# ---------------------------------------------------------------------------
# Archetype 5 — Calibration drift 後設備偏移
# ---------------------------------------------------------------------------
def gen_calibration_drift(rng: random.Random) -> dict[str, Any]:
    broken = rng.choice(TESTERS)
    others = _other_testers(broken)
    product = rng.choice(PRODUCTS)
    spec = rng.choice(["Idsat", "Igate_leak", "Vbreakdown"])
    cal_date = "2026-05-16"
    drift_pct = round(rng.uniform(1.8, 3.5), 1)
    lot = _lot_id(rng)

    fixtures = {
        "query_mes": {
            "default": {"status": "no_data"},
            f"metric=bin_distribution|timerange=last_4h|filter={product}": {
                "summary": f"過去 4 小時 {product} bin 分佈",
                "data": {
                    "Bin 1 (Pass)": "84.0% (-11pp)",
                    "Bin 8 (Leakage)": "11.2% ⚠️ (+10pp 異常增加)",
                    "Bin 5 (Open)": "1.4%",
                },
                "note": "Bin 8 (Leakage / 規格邊界 fail) 增加，不是接觸問題",
            },
            "metric=yield_by_tester|timerange=last_4h": {
                "summary": "各 tester yield",
                "data": {
                    **{t: f"{rng.randint(94, 96)}.{rng.randint(0, 9)}% (正常)" for t in others},
                    broken: f"84.{rng.randint(0, 9)}% ⚠️",
                },
            },
            f"metric=spec_distribution|timerange=last_4h|filter={broken}": {
                "summary": f"{broken} 上 {spec} 分佈",
                "data": f"近 4 小時 {spec} 平均值偏移 {drift_pct}%，分佈整體右移 (非變異變大)，像系統性 offset。",
            },
        },
        "query_tester_status": {
            "default": {"status": "no_data"},
            f"tester_id={broken}": {
                "summary": f"{broken} 狀態",
                "data": {
                    "status": "Running",
                    "firmware": "v8.4.8 (無變更)",
                    "last_calibration": f"{cal_date} ⚠️ (兩天前由 OT 完成的例行年度 calibration)",
                    "calibration_log": "完成記錄 OK，但事後比對標準品有 systematic offset",
                    "self_diagnostic": "Pass (但 self-diag 不檢查絕對精度)",
                    "note": "Tester 本身運轉正常，懷疑 calibration 標準件異常",
                },
            },
            **{
                f"tester_id={t}": {
                    "summary": f"{t} 狀態",
                    "data": {"last_calibration": "2026-04-30 (正常)", "self_diagnostic": "Pass"},
                }
                for t in others
            },
        },
        "query_correlation": {
            "default": {"status": "no_data"},
            f"tester_a={broken}|tester_b={others[0]}|spec={spec}": {
                "summary": f"{broken} vs {others[0]} {spec}",
                "data": {
                    "差異": f"{drift_pct}% ⚠️ (允收 ±1%)",
                    "趨勢": f"差異自 {cal_date} 起出現",
                },
            },
        },
        "query_probe_card": {"default": {"summary": "Probe card", "data": "兩台 tester 上的 probe card 狀態都正常"}},
        "query_handler_metrics": {"default": {"summary": "Handler", "data": "正常"}},
        "query_facility": {"default": {"summary": "廠務", "data": "正常"}},
        "query_ot_network": {"default": {"summary": "OT 網路", "data": "正常"}},
        "query_test_program": {
            "default": {"status": "no_data"},
            f"tester_id={broken}": {
                "summary": f"{broken} test program",
                "data": {"name": f"TP-{product}-v3.5.0", "last_modified": "2026-03-12"},
            },
        },
        "query_wafer_map_status": {"default": {"summary": "Wafer map", "data": "正常"}},
        "query_recent_it_changes": {
            "default": {
                "summary": "近 14 日變更",
                "data": {
                    f"{broken} calibration": f"{cal_date} OT 工程師執行年度 calibration",
                    "Calibration 標準件": "本次使用的標準件 SN-202 經追溯，校驗有效期已過期 30 天 (應 6 個月前送 NIST 認證)",
                    "Test program": "無變更",
                    "結論": "calibration 用了過期標準件，等於把錯誤精度寫進機台",
                },
            },
        },
    }

    return {
        "id": f"random_calibration_{rng.randint(1000, 9999)}",
        "title": f"{broken} 量測 {spec} 偏移 {drift_pct}%",
        "icon": "🎚️",
        "business_summary": f"{broken} 上 {product} 的 {spec} 量測整體偏移 {drift_pct}%，Bin 8 (Leakage fail) 大量增加，疑似誤判好品。",
        "hourly_revenue_impact": _money(rng, 600_000, 1_100_000),
        "incident_message": (
            f"事故通報：今天 2026-05-18 下午，{broken} 上 {product} (批次 {lot}) 的 {spec} "
            f"量測結果整體偏移 {drift_pct}%，Bin 8 (Leakage) 大量增加，疑似誤判好品為不良。"
            f"請查根因。"
        ),
        "fixtures": fixtures,
        "ground_truth": {
            "archetype_id": "calibration_drift",
            "archetype_name": "Calibration 使用過期標準件造成精度漂移",
            "summary": f"OT 工程師於 {cal_date} 對 {broken} 執行年度 calibration，但所用的標準件 SN-202 校驗期已過 30 天，等於把錯誤的精度寫進機台，導致 {spec} 量測系統性偏移 {drift_pct}%，Bin 8 暴增。",
            "key_facts": {
                "broken_tester": broken,
                "spec": spec,
                "drift_pct": drift_pct,
                "cal_date": cal_date,
            },
            "expected_keywords": ["calibration", "校正", "標準件", "過期", spec, broken],
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
ARCHETYPES = {
    "probe_card_eol": gen_probe_card_eol,
    "firmware_drift": gen_firmware_drift,
    "handler_air_pressure": gen_handler_air_pressure,
    "ot_network_crc": gen_ot_network_crc,
    "calibration_drift": gen_calibration_drift,
}


def generate_random_scenario(seed: int | None = None) -> dict[str, Any]:
    """Pick a random archetype and produce a fresh scenario."""
    rng = random.Random(seed) if seed is not None else random.Random()
    archetype_id = rng.choice(list(ARCHETYPES.keys()))
    return ARCHETYPES[archetype_id](rng)
