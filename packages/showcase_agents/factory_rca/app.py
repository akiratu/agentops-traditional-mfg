"""Streamlit UI — 智慧製造廠 IT/OT RCA Agent Demo
v4: rolling notebook + rule-based pre-pass (Hermes-style compression)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from agent import (  # noqa: E402
    ConclusionEvent,
    DoneEvent,
    ErrorEvent,
    FoldedEvent,
    NotebookUpdateEvent,
    PlanEvent,
    PlanStepDoneEvent,
    RAGRetrievalEvent,
    ThoughtEvent,
    TokenStatsEvent,
    ToolCallEvent,
    ToolResultEvent,
    run_agent,
)
from generator import generate_random_scenario  # noqa: E402
from tools import list_scenarios  # noqa: E402

load_dotenv()


@st.cache_resource
def _get_build_info() -> dict:
    """Read current git commit SHA + timestamp for the sidebar watermark.

    Cached for the lifetime of the Streamlit process. Returns 'unknown' if
    `.git` isn't available (e.g. odd deploy environments)."""
    import subprocess
    try:
        repo_dir = str(Path(__file__).parent)
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir, stderr=subprocess.DEVNULL, timeout=3,
        ).decode().strip()
        when = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M", "HEAD"],
            cwd=repo_dir, stderr=subprocess.DEVNULL, timeout=3,
        ).decode().strip()
        subject = subprocess.check_output(
            ["git", "log", "-1", "--format=%s", "HEAD"],
            cwd=repo_dir, stderr=subprocess.DEVNULL, timeout=3,
        ).decode().strip()
        return {"sha": sha, "when": when, "subject": subject}
    except Exception:
        return {"sha": "unknown", "when": "", "subject": ""}


def _md_to_html(text: str) -> str:
    """Minimal markdown → HTML for the notebook display (h2, bullets only)."""
    out_lines = []
    in_list = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("- "):
            if not in_list:
                out_lines.append("<ul>")
                in_list = True
            out_lines.append(f"<li>{stripped[2:]}</li>")
        elif stripped == "":
            if in_list:
                out_lines.append("</ul>")
                in_list = False
        else:
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(f"<p style='margin:4px 0;'>{stripped}</p>")
    if in_list:
        out_lines.append("</ul>")
    return "\n".join(out_lines)

st.set_page_config(
    page_title="智慧製造廠 RCA Agent Demo",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* ════════════════════════════════════════════════════════════
       Design tokens — single source of truth for the whole UI
       ════════════════════════════════════════════════════════════ */
    :root {
        --ink-1: #0f172a;        /* primary text */
        --ink-2: #334155;        /* body text */
        --ink-3: #64748b;        /* muted */
        --ink-4: #94a3b8;        /* very muted */
        --bg-page: #fafafa;
        --bg-card: #ffffff;
        --bg-soft: #f8fafc;
        --border-1: #e2e8f0;
        --border-2: #cbd5e1;
        --brand: #4f46e5;
        --brand-soft: #eef2ff;
        --brand-ink: #3730a3;
        --it: #3b82f6;
        --it-soft: #eff6ff;
        --it-ink: #1e40af;
        --ot: #ec4899;
        --ot-soft: #fdf2f8;
        --ot-ink: #9d174d;
        --success: #10b981;
        --success-soft: #ecfdf5;
        --success-ink: #047857;
        --warning: #f59e0b;
        --warning-soft: #fffbeb;
        --warning-ink: #b45309;
        --danger: #ef4444;
        --danger-soft: #fef2f2;
        --danger-ink: #b91c1c;
        --info: #0891b2;
        --info-soft: #ecfeff;
        --info-ink: #155e75;
        --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
        --shadow-md: 0 2px 8px rgba(15, 23, 42, 0.06);
    }

    /* Light chrome cleanup. Keep Streamlit's own header bar (it owns the
       sidebar collapse/expand toggle) untouched — only hide the deploy
       button + footer + right-side toolbar items. */
    .stDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { visibility: hidden; }

    /* App-wide typography */
    .stMarkdown, .stMarkdown p { color: var(--ink-2); }
    h1, h2, h3, h4, h5 { color: var(--ink-1); letter-spacing: -0.01em; }
    /* Hide Streamlit's auto-added header anchor links (the 🔗 chain icon) */
    .hero h1 a, h1 > a.anchor-link, h2 > a.anchor-link, h3 > a.anchor-link,
    [data-testid="stHeaderActionElements"] { display: none !important; }

    /* ──────────── Hero header ──────────── */
    .hero {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
        color: #ffffff !important; padding: 28px 32px; border-radius: 14px;
        margin: 4px 0 18px; box-shadow: var(--shadow-md);
    }
    .hero * { color: #ffffff !important; }
    .hero .brand {
        font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase;
        opacity: 0.75; margin-bottom: 6px; font-weight: 600;
    }
    .hero h1 { font-size: 28px; margin: 0 0 8px 0; font-weight: 700; }
    .hero .tagline { font-size: 14px; opacity: 0.92; max-width: 720px; line-height: 1.55; }
    .hero .version-pill {
        display: inline-block; background: rgba(255,255,255,0.18);
        font-size: 11px; padding: 3px 10px; border-radius: 10px;
        margin-left: 10px; vertical-align: middle; font-weight: 600;
        letter-spacing: 0.05em;
    }

    /* ──────────── Scenario cards (selectable, white, accent stripe) ──────────── */
    .scenario-card {
        background: var(--bg-card); color: var(--ink-2);
        padding: 20px; border-radius: 12px; margin-bottom: 10px;
        border: 1px solid var(--border-1); border-left: 4px solid var(--ink-3);
        min-height: 200px; box-shadow: var(--shadow-sm);
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }
    .scenario-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
    .scenario-card.preset { border-left-color: var(--it); }
    .scenario-card.random { border-left-color: var(--brand); }
    .scenario-card h3 {
        margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: var(--ink-1);
    }
    .scenario-card p { font-size: 13.5px; line-height: 1.6; color: var(--ink-2); margin: 6px 0; }
    .scenario-card .impact {
        background: var(--danger-soft); color: var(--danger-ink);
        padding: 8px 12px; border-radius: 6px; margin-top: 12px;
        font-size: 13px; font-weight: 600;
        border: 1px solid #fecaca;
    }
    .scenario-card.random .impact {
        background: var(--brand-soft); color: var(--brand-ink); border-color: #c7d2fe;
    }

    /* ──────────── Plan panel ──────────── */
    .plan-box {
        background: var(--bg-card); border: 1px solid var(--border-1);
        border-left: 4px solid var(--brand);
        border-radius: 8px; padding: 14px 16px; margin: 8px 0;
        box-shadow: var(--shadow-sm);
    }
    .plan-box h4 {
        color: var(--brand-ink); margin: 0 0 12px 0; font-size: 14px;
        text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    }
    .plan-step {
        padding: 8px 10px; margin: 6px 0; border-radius: 6px;
        font-size: 13.5px; line-height: 1.5; color: var(--ink-2);
        border: 1px solid transparent;
    }
    .plan-step.pending { background: var(--bg-soft); }
    .plan-step.current {
        background: var(--warning-soft); border-color: #fde68a;
        color: var(--warning-ink); font-weight: 600;
    }
    .plan-step.done { background: var(--success-soft); color: var(--success-ink); }
    .plan-step.done .hypothesis { text-decoration: line-through; opacity: 0.65; }
    .plan-finding {
        font-size: 12.5px; margin-top: 4px; padding-left: 22px;
        font-style: italic; color: var(--ink-3);
    }

    /* ──────────── Timeline items ──────────── */
    .timeline-thought {
        background: var(--bg-card); border: 1px solid var(--border-1);
        border-left: 3px solid var(--ink-3); padding: 12px 16px;
        margin: 8px 0; border-radius: 6px; color: var(--ink-2);
        line-height: 1.6; font-size: 13.5px;
    }
    .timeline-thought b { color: var(--ink-1); font-weight: 600; }

    .tool-call {
        background: var(--bg-soft); border: 1px solid var(--border-1);
        border-left: 3px solid var(--ink-3); padding: 10px 14px;
        margin: 6px 0; border-radius: 6px;
        font-family: 'SF Mono', Menlo, monospace; font-size: 12.5px;
        color: var(--ink-2);
    }
    .tool-call.it {
        background: var(--it-soft); border-left-color: var(--it);
        color: var(--it-ink);
    }
    .tool-call.ot {
        background: var(--ot-soft); border-left-color: var(--ot);
        color: var(--ot-ink);
    }
    .tool-call b { color: var(--ink-1); }

    /* Domain pill (IT / OT) */
    .domain-pill {
        display: inline-block; padding: 2px 8px; border-radius: 10px;
        font-size: 10.5px; font-weight: 700; margin-right: 8px;
        letter-spacing: 0.04em; color: #ffffff !important;
    }
    .domain-pill.it { background: var(--it); }
    .domain-pill.ot { background: var(--ot); }

    /* Folded badge + row */
    .folded-badge {
        display: inline-block; background: var(--brand); color: #ffffff !important;
        font-size: 10.5px; padding: 2px 8px; border-radius: 10px;
        margin-right: 8px; font-weight: 700; letter-spacing: 0.04em;
    }
    .folded-row {
        background: var(--brand-soft); border: 1px solid #c7d2fe;
        border-left: 3px solid var(--brand);
        padding: 8px 12px; margin: 4px 0; border-radius: 6px;
        font-size: 12px; color: var(--brand-ink);
        line-height: 1.5; font-family: 'SF Mono', Menlo, monospace;
    }

    /* ──────────── Notebook ──────────── */
    .notebook-box {
        background: var(--bg-card); border: 1px solid var(--border-1);
        border-left: 4px solid var(--brand);
        border-radius: 8px; padding: 16px 18px; margin: 12px 0;
        font-size: 13px; line-height: 1.65; color: var(--ink-2);
        box-shadow: var(--shadow-sm);
    }
    .notebook-box h4 {
        color: var(--brand-ink); margin: 0 0 10px 0; font-size: 14px;
        text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    }
    .notebook-box h2 {
        color: var(--ink-1); font-size: 13px; margin: 12px 0 4px 0;
        font-weight: 600;
    }
    .notebook-box ul { margin: 4px 0 8px 18px; padding: 0; color: var(--ink-2); }
    .notebook-box li { margin: 2px 0; }
    .notebook-empty {
        background: var(--bg-soft); border: 1px dashed var(--border-2);
        border-radius: 8px; padding: 16px; margin: 12px 0;
        color: var(--ink-3); font-size: 13px; font-style: italic;
        text-align: center;
    }

    /* ──────────── Metrics strip ──────────── */
    .metrics-strip {
        background: var(--ink-1); color: #f1f5f9 !important;
        padding: 16px 20px; border-radius: 10px;
        margin: 8px 0 0 0; display: flex; gap: 36px; align-items: center;
        font-family: 'SF Mono', Menlo, monospace; font-size: 13px;
        flex-wrap: wrap; box-shadow: var(--shadow-md);
    }
    .metrics-strip .metric-cell { min-width: 160px; }
    .metrics-strip * { color: #f1f5f9 !important; }
    .metrics-strip .metric-label {
        font-size: 10.5px; opacity: 0.65; letter-spacing: 0.1em;
        text-transform: uppercase; font-weight: 600;
    }
    .metrics-strip .metric-val { font-size: 20px; font-weight: 700; margin-top: 2px; }
    .metrics-strip .saved-pos { color: #34d399 !important; }
    .metrics-strip .saved-pos * { color: #34d399 !important; }
    .metrics-strip .saved-neg { color: #fbbf24 !important; }
    .metrics-strip .saved-neg * { color: #fbbf24 !important; }

    /* ──────────── Conclusion cards (3-section) ──────────── */
    .conclusion-impact, .conclusion-cause, .conclusion-actions {
        background: var(--bg-card); border: 1px solid var(--border-1);
        border-left: 4px solid var(--ink-3);
        border-radius: 10px; padding: 18px 20px; margin: 12px 0;
        font-size: 14.5px; line-height: 1.7; color: var(--ink-2);
        box-shadow: var(--shadow-sm);
    }
    .conclusion-impact { border-left-color: var(--danger); }
    .conclusion-impact h4 { color: var(--danger-ink); }
    .conclusion-cause { border-left-color: var(--it); }
    .conclusion-cause h4 { color: var(--it-ink); }
    .conclusion-actions { border-left-color: var(--success); }
    .conclusion-actions h4 { color: var(--success-ink); }
    .conclusion-impact h4, .conclusion-cause h4, .conclusion-actions h4 {
        margin: 0 0 10px 0; font-size: 14px;
        text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    }
    .conclusion-actions ol { margin: 8px 0 0 20px; padding: 0; }
    .conclusion-actions li { margin: 6px 0; color: var(--ink-2); }

    /* ──────────── Reveal cards ──────────── */
    .reveal-card {
        background: var(--bg-card); border: 1px solid var(--border-1);
        border-left: 4px solid var(--ink-3);
        border-radius: 10px; padding: 18px 20px; margin: 12px 0;
        font-size: 14.5px; line-height: 1.7; color: var(--ink-2);
        box-shadow: var(--shadow-sm);
    }
    .reveal-card h4 {
        margin: 0 0 10px 0; font-size: 14px;
        text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    }
    .reveal-truth { border-left-color: var(--warning); }
    .reveal-truth h4 { color: var(--warning-ink); }
    .reveal-match.hit { border-left-color: var(--success); }
    .reveal-match.hit h4 { color: var(--success-ink); }
    .reveal-match.partial { border-left-color: var(--warning); }
    .reveal-match.partial h4 { color: var(--warning-ink); }
    .reveal-match.miss { border-left-color: var(--danger); }
    .reveal-match.miss h4 { color: var(--danger-ink); }

    /* ──────────── Savings card ──────────── */
    .savings-card {
        background: var(--bg-card); border: 1px solid var(--border-1);
        border-left: 4px solid var(--brand);
        border-radius: 10px; padding: 18px 20px; margin: 12px 0;
        color: var(--ink-2); box-shadow: var(--shadow-sm);
    }
    .savings-card h4 {
        color: var(--brand-ink); margin: 0 0 12px 0; font-size: 14px;
        text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    }
    .savings-card .big-num {
        font-size: 38px; font-weight: 800; color: var(--brand);
        letter-spacing: -0.02em;
    }

    /* ──────────── RAG panel ──────────── */
    .rag-panel {
        background: var(--bg-card); border: 1px solid var(--border-1);
        border-left: 4px solid var(--info);
        border-radius: 10px; padding: 16px 18px; margin: 12px 0;
        color: var(--ink-2); box-shadow: var(--shadow-sm);
    }
    .rag-panel h4 {
        color: var(--info-ink); margin: 0 0 12px 0; font-size: 14px;
        text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    }
    .rag-card {
        background: var(--bg-soft); border: 1px solid var(--border-1);
        border-left: 3px solid var(--info); border-radius: 6px;
        padding: 12px 14px; margin: 8px 0;
        font-size: 13px; line-height: 1.6; color: var(--ink-2);
    }
    .rag-card .meta {
        font-size: 11px; color: var(--ink-3); letter-spacing: 0.04em;
    }
    .rag-card .title {
        font-weight: 600; margin: 4px 0 8px 0;
        font-size: 13.5px; color: var(--ink-1);
    }
    .rag-card .row { margin: 4px 0; }
    .rag-card .row b { color: var(--ink-1); font-weight: 600; }
    .rag-card .score-pill {
        display: inline-block; background: var(--info); color: #ffffff !important;
        font-size: 10.5px; padding: 2px 8px; border-radius: 10px;
        font-weight: 700; margin-left: 8px; letter-spacing: 0.04em;
    }
    .rag-empty {
        background: var(--bg-soft); border: 1px dashed var(--border-2);
        border-radius: 6px; padding: 12px; margin: 8px 0;
        color: var(--ink-3); font-size: 13px;
        font-style: italic; text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ 設定")

    # API keys: read from env (Streamlit Secrets / .env) and never echo back
    # to the browser. Only show inputs if no env var is present.
    gemini_env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    ollama_env = os.environ.get("OLLAMA_API_KEY") or ""

    if gemini_env:
        api_key = gemini_env  # used for Gemini + RAG embedding
        st.success("🔑 Gemini key 已由環境變數設定")
    else:
        api_key = st.text_input(
            "Gemini API Key (RAG embedding 永遠需要)", type="password",
            help="本機開發用。正式部署請改用環境變數 GEMINI_API_KEY 或 Streamlit Secrets。",
        )

    # Provider + model selection
    provider_choice = st.radio(
        "LLM Provider",
        options=["Gemini", "Ollama Cloud"],
        horizontal=True,
        help="Embedding (RAG) 永遠用 Gemini。這裡選的是主 agent + notebook 摘要器。",
    )
    if provider_choice == "Gemini":
        model = st.selectbox(
            "Model",
            options=[
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.0-flash-exp",
                "gemini-2.5-pro",
                "gemma-3-27b-it",
            ],
            index=0,
        )
    else:
        model = st.selectbox(
            "Model (Ollama Cloud)",
            options=[
                "gemma4:31b-cloud",
                "gpt-oss:120b-cloud",
                "qwen3:30b-cloud",
                "deepseek-v3.1:671b-cloud",
            ],
            index=0,
            help="Ollama Cloud 模型名稱需帶 `-cloud` 後綴。",
        )
        if ollama_env:
            st.success("🔑 Ollama key 已由環境變數設定")
        else:
            ollama_key_input = st.text_input(
                "Ollama API Key", type="password",
                help="本機開發用。正式部署請改用環境變數 OLLAMA_API_KEY。",
            )
            if ollama_key_input:
                os.environ["OLLAMA_API_KEY"] = ollama_key_input
    max_iter = st.slider("最大調查步驟", 4, 20, 15)
    enable_rag = st.toggle(
        "🔎 啟用 RAG 歷史案例檢索",
        value=True,
        help="開啟後，事故一進來會先檢索過去類似事故 / 維修紀錄當 Agent 的背景參考。",
    )
    st.caption("RAG corpus 共 18 篇歷史紀錄（5 個根因原型 + 不相關案例）。")
    st.divider()
    st.markdown(
        "**🎲 隨機事故**\n\n"
        "5 個根因原型隨機產生，真實答案藏起來。\n\n"
        "**🔎 RAG**：開頭翻歷史案例。\n\n"
        "**📋 Plan**：Agent 自擬計畫、邊查邊打勾。\n\n"
        "**🗜️ Compression**：邊查邊壓縮舊記憶。"
    )
    # ─── Build info watermark ───
    build = _get_build_info()
    if build["sha"] != "unknown":
        st.divider()
        st.caption(
            f"📦 Build `{build['sha']}` · {build['when']}<br/>"
            f"<span style='font-size:11px;opacity:0.7;'>{build['subject']}</span>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Hero header
_build_for_hero = _get_build_info()
_version_pill = (
    f'<span class="version-pill">v · {_build_for_hero["sha"]}</span>'
    if _build_for_hero["sha"] != "unknown" else ""
)
st.markdown(
    f"""
    <div class="hero">
        <div class="brand">智慧製造 RCA 平台 · 內部 Demo</div>
        <h1>AI 根因分析 Agent{_version_pill}</h1>
        <div class="tagline">
            Agent 自擬計畫、跨 IT / OT 系統真實調查、即時壓縮上下文、檢索歷史案例 (RAG)、揭曉根因比對。
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("active_scenario", None)
ss.setdefault("events", [])
ss.setdefault("running", False)
ss.setdefault("plan_state", {"steps": [], "current_index": None})
ss.setdefault("compression_enabled_run", True)
ss.setdefault("rag_enabled_run", True)


def reset():
    ss.active_scenario = None
    ss.events = []
    ss.running = False
    ss.plan_state = {"steps": [], "current_index": None}


def pick_preset(sc: dict) -> None:
    ss.active_scenario = sc
    ss.events = []
    ss.running = True
    ss.plan_state = {"steps": [], "current_index": None}
    ss.compression_enabled_run = compression_enabled
    ss.rag_enabled_run = enable_rag


def pick_random() -> None:
    ss.active_scenario = generate_random_scenario()
    ss.events = []
    ss.running = True
    ss.plan_state = {"steps": [], "current_index": None}
    ss.compression_enabled_run = compression_enabled
    ss.rag_enabled_run = enable_rag


preset_scenarios = list_scenarios()

# ---------------------------------------------------------------------------
# Scenario picker
# ---------------------------------------------------------------------------
if ss.active_scenario is None:
    # Prominent compression toggle above the scenario picker (must be set BEFORE clicking go)
    tcol1, tcol2 = st.columns([3, 1])
    with tcol1:
        st.markdown(
            """
            <div style="background:#f5f3ff;border:2px solid #8b5cf6;border-radius:8px;
                        padding:14px 18px;margin:8px 0;color:#4c1d95;">
                <b>🗜️ 上下文壓縮 (Context Compression)</b><br/>
                <span style="font-size:13px;">
                舊的 tool 結果會被 LLM 整理成結構化筆記本（Gemini 用 <code>gemini-2.0-flash</code>、Ollama 用主 model），節省 60-80% token。
                <b>請在按下「派 AI 去查」之前決定要不要開</b>，執行中無法切換。
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with tcol2:
        compression_enabled = st.toggle(
            "啟用壓縮",
            value=True,
            key="compression_toggle",
            help="ON：邊查邊壓縮 / OFF：完整上下文都送 Gemini",
        )
        st.caption(f"目前：**{'🟢 ON' if compression_enabled else '⚪ OFF'}**")

    st.subheader("📋 選一個事故情境")
    cols = st.columns(3)

    with cols[0]:
        sc = preset_scenarios[0]
        st.markdown(
            f"""
            <div class="scenario-card preset">
                <h3>{sc['icon']} {sc['title']}</h3>
                <p>{sc['business_summary']}</p>
                <div class="impact">💸 影響：{sc['hourly_revenue_impact']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button("▶ 派 AI 去查 (固定情境)", key=f"go_{sc['id']}",
                  use_container_width=True, disabled=not api_key,
                  on_click=pick_preset, args=(sc,))

    with cols[1]:
        sc = preset_scenarios[1]
        st.markdown(
            f"""
            <div class="scenario-card preset">
                <h3>{sc['icon']} {sc['title']}</h3>
                <p>{sc['business_summary']}</p>
                <div class="impact">💸 影響：{sc['hourly_revenue_impact']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button("▶ 派 AI 去查 (固定情境)", key=f"go_{sc['id']}",
                  use_container_width=True, disabled=not api_key,
                  on_click=pick_preset, args=(sc,))

    with cols[2]:
        st.markdown(
            """
            <div class="scenario-card random">
                <h3>🎲 隨機事故</h3>
                <p>從 5 個根因原型隨機產生一個全新事故：probe card 壽命 / 韌體沒同步 / 廠務壓縮機 / 網路 CRC / calibration 漂移。</p>
                <p><b>真實根因藏起來，連你也不知道答案，Agent 真的要查。</b></p>
                <div class="impact">🎭 每次都不一樣 · 跑完揭曉答案</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button("🎲 產生隨機事故並派 AI 去查", key="go_random",
                  use_container_width=True, disabled=not api_key,
                  on_click=pick_random)

    if not api_key:
        st.warning("⚠️ 請先在左側設定 Gemini API Key")

else:
    # -----------------------------------------------------------------------
    # Active investigation
    # -----------------------------------------------------------------------
    active = ss.active_scenario

    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.subheader(f"{active['icon']} {active['title']}")
        st.caption(f"💸 影響：{active['hourly_revenue_impact']}")
        with st.expander("📨 事故通報內容", expanded=False):
            st.write(active["incident_message"])
    with top_r:
        st.button("← 回主選單", use_container_width=True, on_click=reset,
                  help="回去重新選情境或產生新的隨機事故")

    # Metrics strip (token stats)
    metrics_placeholder = st.empty()

    # RAG panel (above plan/timeline)
    rag_placeholder = st.empty()

    # Two columns: plan + notebook stacked (left) | timeline (right)
    plan_col, timeline_col = st.columns([1, 2])

    with plan_col:
        st.markdown("### 📋 Agent 調查計畫")
        plan_container = st.empty()
        st.markdown("### 📔 Agent 工作筆記本")
        st.caption("Agent 邊查邊整理的結構化摘要。**整份注入主 agent context、取代中間所有 turn**（Hermes 「drop middle + summary」做法）。")
        notebook_container = st.empty()

    with timeline_col:
        st.markdown("### 🧠 即時調查 Timeline")
        timeline_container = st.container()

    conclusion_container = st.container()
    reveal_container = st.container()

    # ---- per-seq tool result slots (so they can be updated when folded)
    tool_slots: dict = {}
    tool_data: dict[int, dict] = {}
    folded_seqs: set[int] = set()
    folded_rules: dict[int, str] = {}
    # Wrap notebook text in a dict so cb closure can update via mutation
    nb_state: dict[str, str] = {"text": ""}

    # ---- token stats tracking
    token_history: list[dict] = []  # list of {iter, raw, sent}

    def fmt_int(n: int) -> str:
        return f"{n:,}"

    def render_metrics() -> None:
        if not token_history:
            metrics_placeholder.empty()
            return
        latest = token_history[-1]
        raw = latest["raw"]
        sent = latest["sent"]
        saved = max(raw - sent, 0)
        saved_pct = (saved / raw * 100.0) if raw else 0.0
        cls = "saved-pos" if saved_pct >= 5 else "saved-neg"
        note = ""
        if saved_pct < 5 and len(folded_seqs) == 0:
            note = "（上下文還小、尚無 tool 結果可折進筆記本）"
        elif saved_pct < 5:
            note = "（筆記本本身也佔 token，幾乎打平）"
        comp_label = "ON" if ss.compression_enabled_run else "OFF"
        note_html = f' · <span style="font-size:11px;">{note}</span>' if note else ""
        metrics_placeholder.markdown(
            f"""
            <div class="metrics-strip">
                <div class="metric-cell">
                    <div class="metric-label">📦 完整上下文（估計 token）</div>
                    <div class="metric-val">{fmt_int(raw)}</div>
                </div>
                <div class="metric-cell">
                    <div class="metric-label">📤 實際送 Gemini（估計 token）</div>
                    <div class="metric-val">{fmt_int(sent)}</div>
                </div>
                <div class="metric-cell {cls}">
                    <div class="metric-label">💰 省下</div>
                    <div class="metric-val">↓ {fmt_int(saved)} ({saved_pct:.0f}%)</div>
                </div>
            </div>
            <div style="font-size:12px; opacity:0.7; padding:4px 4px 12px 4px;">
                iter {latest['iter']+1} · 壓縮 {comp_label}{note_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- renderers ----
    def render_plan() -> None:
        steps = ss.plan_state["steps"]
        cur = ss.plan_state["current_index"]
        if not steps:
            plan_container.markdown(
                '<div class="plan-box"><i>等 Agent 擬計畫...</i></div>',
                unsafe_allow_html=True,
            )
            return
        html_parts = ['<div class="plan-box"><h4>🗺️ Agent 自己擬的調查步驟</h4>']
        for i, step in enumerate(steps):
            if step.get("done"):
                status_cls = "done"
                icon = "✅"
            elif i == cur:
                status_cls = "current"
                icon = "⏳"
            else:
                status_cls = "pending"
                icon = "⚪"
            html_parts.append(
                f'<div class="plan-step {status_cls}">'
                f'<div>{icon} <span class="hypothesis"><b>步驟 {i+1}</b>：{step.get("hypothesis", "")}</span></div>'
                f'<div style="font-size:12px;opacity:0.85;padding-left:22px;">↳ {step.get("action", "")}</div>'
            )
            if step.get("finding"):
                html_parts.append(f'<div class="plan-finding">💡 發現：{step["finding"]}</div>')
            html_parts.append('</div>')
        html_parts.append('</div>')
        plan_container.markdown("".join(html_parts), unsafe_allow_html=True)

    rag_state: dict[str, list] = {"results": []}

    def render_rag() -> None:
        results = rag_state["results"]
        if not ss.rag_enabled_run:
            rag_placeholder.empty()
            return
        if not results:
            rag_placeholder.markdown(
                '<div class="rag-empty">🔎 沒找到相似度足夠的歷史案例（min_score=0.55）</div>',
                unsafe_allow_html=True,
            )
            return
        cards_html = "".join(
            f'<div class="rag-card">'
            f'<span class="meta">[{r["id"]}] · {r["date"]} · {r.get("severity", "")}</span>'
            f'<span class="score-pill">相似度 {int(r["score"]*100)}%</span>'
            f'<div class="title">📌 {r["title"]}</div>'
            f'<div class="row">🚨 <b>症狀</b>：{r.get("symptom", "")}</div>'
            f'<div class="row">🎯 <b>根因</b>：{r.get("root_cause", "")}</div>'
            f'<div class="row">✅ <b>解法</b>：{r.get("fix", "")}</div>'
            f'</div>'
            for r in results
        )
        rag_placeholder.markdown(
            f'<div class="rag-panel">'
            f'<h4>🔎 Agent 找到 {len(results)} 件相似歷史案例（事故進來時自動 RAG 檢索）</h4>'
            f'{cards_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    def render_notebook() -> None:
        if not nb_state["text"]:
            notebook_container.markdown(
                '<div class="notebook-empty">尚未開始壓縮 — 前 2 個 tool 結果會保留完整版，第 3 個開始才會折進筆記本</div>',
                unsafe_allow_html=True,
            )
            return
        notebook_container.markdown(
            f'<div class="notebook-box">'
            f'<h4>📔 Agent 工作筆記本（折進 {len(folded_seqs)} 個 tool 結果）</h4>'
            f'{_md_to_html(nb_state["text"])}'
            f'</div>',
            unsafe_allow_html=True,
        )

    def render_tool_result_slot(seq: int) -> None:
        """Render tool result for seq into its slot. If folded into notebook,
        show a compact badge instead of the full JSON."""
        slot = tool_slots.get(seq)
        if slot is None:
            return
        d = tool_data.get(seq)
        if not d:
            return
        with slot.container():
            if seq in folded_seqs:
                rule_line = folded_rules.get(seq, "")
                st.markdown(
                    f'<div class="folded-row">'
                    f'<span class="folded-badge">🗒️ 已折進筆記本</span>'
                    f'{rule_line}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                with st.expander(f"     ↳ 原始 {d['tool_name']} 結果 (壓縮前)", expanded=False):
                    st.json(d["result"])
            else:
                with st.expander(f"     ↳ {d['tool_name']} 結果", expanded=False):
                    st.json(d["result"])

    def render_timeline_event(ev) -> None:
        with timeline_container:
            if isinstance(ev, ThoughtEvent):
                st.markdown(
                    f'<div class="timeline-thought"><b>🤖 Agent：</b>{ev.text}</div>',
                    unsafe_allow_html=True,
                )
            elif isinstance(ev, ToolCallEvent):
                cls = ev.domain.lower() if ev.domain in ("IT", "OT") else ""
                domain_label = "🖥️ IT" if ev.domain == "IT" else "🔧 OT"
                args_str = ", ".join(f"{k}={v!r}" for k, v in ev.args.items()) if ev.args else ""
                st.markdown(
                    f'<div class="tool-call {cls}">'
                    f'<span class="domain-pill {cls}">{domain_label}</span>'
                    f'呼叫 <b>{ev.tool_name}</b>({args_str})'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            elif isinstance(ev, ToolResultEvent):
                # Allocate a slot for this seq, store data, then render
                tool_data[ev.seq] = {"tool_name": ev.tool_name, "result": ev.result}
                slot = st.empty()
                tool_slots[ev.seq] = slot
                render_tool_result_slot(ev.seq)
            elif isinstance(ev, ErrorEvent):
                st.error(ev.message)

    def render_conclusion(conc: ConclusionEvent) -> None:
        with conclusion_container:
            st.markdown("---")
            st.markdown("## 🎯 Agent 的分析結論")
            st.markdown(
                f'<div class="conclusion-impact"><h4>🔴 業務影響</h4>{conc.business_impact}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="conclusion-cause"><h4>🔍 根本原因</h4>{conc.root_cause}</div>',
                unsafe_allow_html=True,
            )
            actions_html = "".join(f"<li>{a}</li>" for a in conc.actions)
            st.markdown(
                f'<div class="conclusion-actions"><h4>✅ 建議行動</h4><ol>{actions_html}</ol></div>',
                unsafe_allow_html=True,
            )

    def grade(agent_cause: str, gt: dict) -> tuple[str, str, list[str]]:
        keywords = gt.get("expected_keywords", [])
        text = agent_cause.lower()
        hits = [k for k in keywords if k.lower() in text]
        ratio = len(hits) / max(len(keywords), 1)
        if ratio >= 0.5:
            return "hit", "✅ 命中", hits
        if ratio >= 0.25:
            return "partial", "⚠️ 部分命中", hits
        return "miss", "❌ 未命中", hits

    def render_reveal(conc: ConclusionEvent) -> None:
        gt = active.get("ground_truth")
        if not gt:
            return
        with reveal_container:
            st.markdown("---")
            st.markdown("## 🎭 答案揭曉")
            tier, label, hits = grade(conc.root_cause, gt)
            kw_str = "、".join(f"<code>{k}</code>" for k in gt.get("expected_keywords", []))
            hits_str = "、".join(f"<code>{h}</code>" for h in hits) if hits else "（無）"
            st.markdown(
                f'<div class="reveal-card reveal-truth">'
                f'<h4>🎲 系統設定的真實根因（{gt.get("archetype_name", "")}）</h4>'
                f'{gt.get("summary", "")}'
                f'<br/><br/><b>預期關鍵字</b>：{kw_str}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="reveal-card reveal-match {tier}">'
                f'<h4>{label}</h4>'
                f'Agent 在結論中命中的關鍵字：{hits_str}'
                f'</div>',
                unsafe_allow_html=True,
            )

    def render_savings_card() -> None:
        if not token_history:
            return
        # Sum across all iterations
        total_raw = sum(t["raw"] for t in token_history)
        total_sent = sum(t["sent"] for t in token_history)
        saved = max(total_raw - total_sent, 0)
        saved_pct = (saved / total_raw * 100.0) if total_raw else 0.0
        folded_count = len(folded_seqs)
        comp_status = "ON" if ss.compression_enabled_run else "OFF"
        with reveal_container:
            st.markdown(
                f"""
                <div class="savings-card">
                    <h4>🗜️ 上下文壓縮成果 (Compression {comp_status})</h4>
                    <p>整場調查 {len(token_history)} 輪 Gemini 呼叫累計：</p>
                    <div style="display:flex; gap:32px; align-items:center; flex-wrap:wrap;">
                        <div>
                            <div style="font-size:12px;opacity:0.7;">不壓縮會送出（估計 token）</div>
                            <div style="font-size:22px;font-weight:600;">{fmt_int(total_raw)}</div>
                        </div>
                        <div>
                            <div style="font-size:12px;opacity:0.7;">實際送出（估計 token）</div>
                            <div style="font-size:22px;font-weight:600;">{fmt_int(total_sent)}</div>
                        </div>
                        <div>
                            <div style="font-size:12px;opacity:0.7;">省下</div>
                            <div class="big-num">{saved_pct:.0f}%</div>
                            <div style="font-size:13px;">({fmt_int(saved)} tokens · {folded_count} 個 tool 結果折進筆記本)</div>
                        </div>
                    </div>
                    <p style="margin-top:14px; font-size:13px;">
                        💡 <b>Hermes-style drop middle + summary</b>：把中間所有 turn 換成一份結構化筆記本注入。
                        準確度仍由「答案揭曉」面板的關鍵字命中率驗證。
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ---- replay cached events if not running ----
    if not ss.running:
        for ev in ss.events:
            if isinstance(ev, FoldedEvent):
                for s, rule in zip(ev.seqs, ev.rule_summaries):
                    folded_seqs.add(s)
                    folded_rules[s] = rule
            elif isinstance(ev, NotebookUpdateEvent):
                nb_state["text"] = ev.notebook
            elif isinstance(ev, RAGRetrievalEvent):
                rag_state["results"] = ev.results
            elif isinstance(ev, ToolResultEvent):
                tool_data[ev.seq] = {"tool_name": ev.tool_name, "result": ev.result}
            elif isinstance(ev, TokenStatsEvent):
                token_history.append({"iter": ev.iteration, "raw": ev.raw_tokens, "sent": ev.sent_tokens})

        render_metrics()
        render_rag()
        render_notebook()
        if ss.plan_state["steps"]:
            render_plan()
        for ev in ss.events:
            render_timeline_event(ev)
        for ev in ss.events:
            if isinstance(ev, ConclusionEvent):
                render_conclusion(ev)
                render_reveal(ev)
                render_savings_card()

    # ---- run the agent now ----
    else:
        render_rag()  # empty until RAGRetrievalEvent arrives
        render_plan()
        render_notebook()

        with timeline_container:
            status = st.status("🧠 AI Agent 開始調查...", expanded=True)

        captured: dict = {"conclusion": None, "events": []}

        def cb(ev):
            captured["events"].append(ev)
            if isinstance(ev, TokenStatsEvent):
                token_history.append({"iter": ev.iteration, "raw": ev.raw_tokens, "sent": ev.sent_tokens})
                render_metrics()
                return
            if isinstance(ev, RAGRetrievalEvent):
                rag_state["results"] = ev.results
                render_rag()
                return
            if isinstance(ev, FoldedEvent):
                for s, rule in zip(ev.seqs, ev.rule_summaries):
                    folded_seqs.add(s)
                    folded_rules[s] = rule
                    render_tool_result_slot(s)
                return
            if isinstance(ev, NotebookUpdateEvent):
                nb_state["text"] = ev.notebook
                render_notebook()
                return
            if isinstance(ev, PlanEvent):
                ss.plan_state["steps"] = [
                    {"hypothesis": s["hypothesis"], "action": s["action"], "done": False, "finding": ""}
                    for s in ev.steps
                ]
                ss.plan_state["current_index"] = 0
                render_plan()
                return
            if isinstance(ev, PlanStepDoneEvent):
                idx = ev.step_index
                if 0 <= idx < len(ss.plan_state["steps"]):
                    ss.plan_state["steps"][idx]["done"] = True
                    ss.plan_state["steps"][idx]["finding"] = ev.finding
                    ss.plan_state["current_index"] = idx + 1 if idx + 1 < len(ss.plan_state["steps"]) else None
                render_plan()
                return
            if isinstance(ev, ConclusionEvent):
                captured["conclusion"] = ev
                return
            if isinstance(ev, DoneEvent):
                return
            render_timeline_event(ev)

        run_agent(
            scenario=ss.active_scenario,
            api_key=api_key,
            model=model,
            max_iterations=max_iter,
            on_event=cb,
            compression_enabled=ss.compression_enabled_run,
            enable_rag=ss.rag_enabled_run,
        )

        for s in ss.plan_state["steps"]:
            if not s["done"]:
                s["done"] = True
                s["finding"] = s.get("finding") or "（結束時自動標記）"
        ss.plan_state["current_index"] = None
        render_plan()

        with timeline_container:
            status.update(label="✅ 調查完成", state="complete", expanded=True)

        ss.events = captured["events"]
        ss.running = False

        if captured["conclusion"] is not None:
            render_conclusion(captured["conclusion"])
            render_reveal(captured["conclusion"])
            render_savings_card()
