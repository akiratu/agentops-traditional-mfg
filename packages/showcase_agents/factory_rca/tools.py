"""Mock RCA tools backed by scenario fixture data.

Each tool reads from the active scenario's `fixtures` dict.
Fixture keys are built as `arg1=value|arg2=value|...` (sorted by arg name);
if no match found, falls back to `default`.

Tool declarations are exposed as provider-agnostic `ToolSpec` objects.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from providers import ToolSpec

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

# domain tag for UI rendering
IT = "IT"
OT = "OT"

TOOL_DOMAIN: dict[str, str] = {
    "query_mes": IT,
    "query_test_program": IT,
    "query_correlation": IT,
    "query_wafer_map_status": IT,
    "query_recent_it_changes": IT,
    "query_tester_status": OT,
    "query_handler_metrics": OT,
    "query_probe_card": OT,
    "query_facility": OT,
    "query_ot_network": OT,
}


def load_scenario(scenario_id: str) -> dict[str, Any]:
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def list_scenarios() -> list[dict[str, Any]]:
    out = []
    for f in sorted(SCENARIOS_DIR.glob("*.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def resolve_scenario(scenario_or_id: Any) -> dict[str, Any]:
    """Accept either a scenario dict (random-generated) or a string ID (JSON file)."""
    if isinstance(scenario_or_id, dict):
        return scenario_or_id
    return load_scenario(scenario_or_id)


def _parse_key(key: str) -> frozenset[tuple[str, str]]:
    """Parse 'k1=v1|k2=v2' → frozenset of (k, v) — order-independent."""
    if not key:
        return frozenset()
    pairs = []
    for part in key.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            pairs.append((k.strip(), v.strip()))
    return frozenset(pairs)


def _args_to_set(args: dict[str, Any]) -> frozenset[tuple[str, str]]:
    return frozenset((k, str(v).strip()) for k, v in args.items() if v is not None and v != "")


def dispatch_tool(scenario: Any, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Look up the tool result in scenario fixtures (order-independent arg matching).

    `scenario` can be a scenario dict OR a scenario ID string.
    """
    if tool_name in ("submit_conclusion", "submit_plan", "mark_plan_step_done"):
        return {"status": "ok"}

    scenario = resolve_scenario(scenario)
    fixtures = scenario.get("fixtures", {}).get(tool_name, {})
    target = _args_to_set(args)

    # exact match first
    for fixture_key, value in fixtures.items():
        if fixture_key == "default":
            continue
        if _parse_key(fixture_key) == target:
            return value

    # then subset match (model passed extra args we don't care about)
    for fixture_key, value in fixtures.items():
        if fixture_key == "default":
            continue
        parsed = _parse_key(fixture_key)
        if parsed and parsed.issubset(target):
            return value

    if "default" in fixtures:
        return fixtures["default"]
    return {
        "status": "no_data",
        "hint": f"此工具 ({tool_name}) 沒有此參數組合的資料，請嘗試不同參數或其他工具",
    }


# ---------------------------------------------------------------------------
# Tool declarations (provider-agnostic)
# ---------------------------------------------------------------------------

def _decl(name: str, description: str, properties: dict[str, dict[str, Any]],
          required: list[str] | None = None) -> ToolSpec:
    """Build a ToolSpec. `properties` uses lowercase JSON-Schema type names
    (e.g. 'string', 'integer', 'array', 'object'). The provider layer takes
    care of any vendor-specific case conversion."""
    return ToolSpec(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    )


def build_function_declarations() -> list[ToolSpec]:
    return [
        # ---------- IT side ----------
        _decl(
            "query_mes",
            "🖥️ IT — 查詢 MES (製造執行系統) 的統計數據，例如 bin 分佈、yield、lot 歷史。",
            {
                "metric": {"type": "string",
                           "description": "要查的指標，例如 bin_distribution / yield_by_tester / bin5_by_tester / lot_history"},
                "timerange": {"type": "string",
                              "description": "時間範圍，例如 last_4h / last_24h"},
                "filter": {"type": "string",
                           "description": "選填過濾條件，例如 product 名稱或 lot ID"},
            },
            required=["metric", "timerange"],
        ),
        _decl(
            "query_test_program",
            "🖥️ IT — 查詢某 tester 上跑的 test program 名稱、版本、最後修改時間。",
            {"tester_id": {"type": "string", "description": "Tester ID，例如 Tester-7"}},
            required=["tester_id"],
        ),
        _decl(
            "query_correlation",
            "🖥️ IT — 比對兩台 tester 對同一規格的量測結果，找出系統性偏移。",
            {
                "tester_a": {"type": "string", "description": "第一台 tester ID"},
                "tester_b": {"type": "string", "description": "第二台 tester ID"},
                "spec": {"type": "string", "description": "要比對的規格名稱，例如 Vth / Idsat"},
            },
            required=["tester_a", "tester_b", "spec"],
        ),
        _decl(
            "query_wafer_map_status",
            "🖥️ IT — 查詢 wafer map 上傳狀態 (用於檢查 OT→IT 資料流是否正常)。",
            {"lot_id": {"type": "string", "description": "選填 lot ID"}},
        ),
        _decl(
            "query_recent_it_changes",
            "🖥️ IT — 查詢近期 IT 變更紀錄 (部署、設定、保養門檻、韌體升級通知等)。",
            {},
        ),
        # ---------- OT side ----------
        _decl(
            "query_tester_status",
            "🔧 OT — 查詢 tester 設備狀態，包含韌體版本、校正、自我診斷、安裝的 probe card。",
            {"tester_id": {"type": "string", "description": "Tester ID，例如 Tester-7"}},
            required=["tester_id"],
        ),
        _decl(
            "query_handler_metrics",
            "🔧 OT — 查詢 tester handler (送料機構) 動作指標：index time、pick & place 時間、氣壓、真空。",
            {"tester_id": {"type": "string", "description": "Tester ID"}},
            required=["tester_id"],
        ),
        _decl(
            "query_probe_card",
            "🔧 OT — 查詢 probe card 狀態：touchdown 次數、接觸電阻、安裝日期。需要先用 query_tester_status 取得 probe card ID。",
            {"card_id": {"type": "string", "description": "Probe card ID，例如 PC-7-042"}},
            required=["card_id"],
        ),
        _decl(
            "query_facility",
            "🔧 OT — 查詢廠務設施狀態：壓縮機、UPS、冷卻、無塵室溫濕度。",
            {"item": {"type": "string", "description": "設施項目，例如 cleanroom_B / compressor_main"}},
            required=["item"],
        ),
        _decl(
            "query_ot_network",
            "🔧 OT — 查詢 OT 網路狀態：SECS/GEM 訊號、CRC error、switch port 狀態。",
            {"segment": {"type": "string", "description": "選填網段，例如 floor_B"}},
        ),
        # ---------- Special: planning ----------
        _decl(
            "submit_plan",
            "📋 在開始任何調查工具之前，先呼叫此工具提交『調查計畫』。3-5 步，每步說明假設與要做什麼。整個事故只呼叫一次。",
            {
                "steps": {
                    "type": "array",
                    "description": "調查步驟清單，依執行順序排列。",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hypothesis": {
                                "type": "string",
                                "description": "這一步要驗證的假設 (用主管聽得懂的話)，例如『先看哪幾台機台出問題』",
                            },
                            "action": {
                                "type": "string",
                                "description": "預計要查什麼系統 / 資料，例如『查 MES bin 分佈、yield by tester』",
                            },
                        },
                        "required": ["hypothesis", "action"],
                    },
                },
            },
            required=["steps"],
        ),
        _decl(
            "mark_plan_step_done",
            "✅ 每完成一個計畫步驟時呼叫，把那一步打勾並寫下發現。下一步進行前再次呼叫此工具。",
            {
                "step_index": {
                    "type": "integer",
                    "description": "計畫步驟的 index (從 0 開始)。",
                },
                "finding": {
                    "type": "string",
                    "description": "這一步的關鍵發現，1 句話。",
                },
            },
            required=["step_index", "finding"],
        ),
        # ---------- Special: terminate ----------
        _decl(
            "submit_conclusion",
            "✅ 完成分析後呼叫此工具提交最終結論。所有欄位必須為繁體中文、主管聽得懂的話。",
            {
                "business_impact": {
                    "type": "string",
                    "description": "業務影響：用主管的語言說明這個事故對生意造成什麼後果 (1-2 句)。",
                },
                "root_cause": {
                    "type": "string",
                    "description": "根本原因：用主管聽得懂的話說明真正的原因 (2-3 句)。",
                },
                "actions": {
                    "type": "array",
                    "description": "建議行動清單 (3-5 項，依優先順序)。每項為一段繁體中文。",
                    "items": {"type": "string"},
                },
            },
            required=["business_impact", "root_cause", "actions"],
        ),
    ]
