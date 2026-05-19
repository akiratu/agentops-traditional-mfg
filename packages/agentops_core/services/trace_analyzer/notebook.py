"""Trace Analyzer notebook helpers.

Builds the initial 4-section notebook from known facts so the agent doesn't
waste tool calls re-deriving them. The agent will then `update_notebook` as
it learns more.
"""

from __future__ import annotations


def build_initial_notebook(
    *,
    anomaly_summary: str,
    agent_purpose: str,
    skill_version: int,
    related_trace_count: int,
) -> str:
    return (
        "## 🔍 已查到什麼\n"
        f"- [signal] {anomaly_summary}\n"
        f"- [agent] purpose: {agent_purpose}\n"
        f"- [skill] currently on v{skill_version}\n"
        f"- [traces] {related_trace_count} related traces flagged\n"
        "\n"
        "## 💡 目前推論\n"
        "資料不足 — 需要先看實際 trace 內容\n"
        "\n"
        "## ❓ 還需驗證\n"
        "- search_traces 看最近異常分布\n"
        "- fetch_trace_detail 至少一個失敗 trace 看完整 prompt+output\n"
        "- fetch_skill_detail 確認當前 prompt 內容\n"
        "- fetch_past_findings 看有沒有類似案例\n"
        "\n"
        "## 🚫 已排除\n"
        "(尚無)\n"
    )
