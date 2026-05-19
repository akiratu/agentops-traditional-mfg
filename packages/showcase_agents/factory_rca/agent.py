"""Provider-agnostic RCA agent loop with rolling-notebook context compression.

Flow:
1. Optional RAG retrieval (similar past cases injected as user context)
2. Planning — agent calls `submit_plan` with 3-5 steps
3. Execution — ReAct loop, tools + `mark_plan_step_done`
4. Termination — `submit_conclusion`

Compression: Hermes-style "drop middle + insert notebook" — older tool
exchanges are dropped from context and replaced by a single user message
carrying an LLM-generated structured notebook summary.

The LLM is accessed exclusively through `providers.LLMProvider`, so swapping
to OpenAI / Anthropic / Ollama later only needs a new provider subclass.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

import rag
from providers import (
    ChatMessage,
    FunctionCall,
    FunctionResponse,
    LLMProvider,
    ToolSpec,
    make_provider,
)
from tools import (
    TOOL_DOMAIN,
    build_function_declarations,
    dispatch_tool,
    resolve_scenario,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

KEEP_RECENT_TOOL_RESPONSES = 2

CONTEXT_COMPACTION_PREAMBLE = (
    "[CONTEXT COMPACTION — REFERENCE ONLY] 之前的調查紀錄已被壓縮成下面這份"
    "結構化摘要。請把它當作背景參考（不要重複裡面已查過的工具），然後**從最新"
    "的 function_response 之後繼續行動**。"
)

NOTEBOOK_PROMPT = """你是 Agent 的「記憶整理助手」。基於既有筆記本與新查到的事，產出一份更新版的結構化筆記本（繁體中文）。

規則：
- 必須保留所有舊筆記本的有用內容，把新查到的事**併入對應段落**
- 用條列、簡潔；不要加前言或結語
- 若某段沒有內容就寫「（無）」
- 若新資料與舊推論衝突，更新「目前推論」並標註原因
- 重要：不要加 markdown code fence，直接輸出文字

筆記本結構（必須完整保留這 4 段）：

## 🔍 已查到什麼
- 條列每個重要發現，用「[tool_name] 摘要」格式

## 💡 目前推論
- 1-2 句說明目前最可能的根因方向（若資料還不夠就寫「資料不足」）

## ❓ 還需驗證
- 條列下一步可能要查的方向

## 🚫 已排除
- 條列已經排除的可能性與理由

═══════════════════════════════════
事故通報（不會變）：
{incident}

既有筆記本（若無則第一次建立）：
{prior_notebook}

新查到的事（一行式預先摘要）：
{new_entries}

═══════════════════════════════════
請直接輸出新版筆記本（繁中、保持 4 段結構、簡潔）："""


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@dataclass
class ThoughtEvent:
    text: str = ""
    kind: Literal["thought"] = "thought"


@dataclass
class PlanEvent:
    steps: list[dict[str, str]] = field(default_factory=list)
    kind: Literal["plan"] = "plan"


@dataclass
class PlanStepDoneEvent:
    step_index: int = 0
    finding: str = ""
    kind: Literal["plan_step_done"] = "plan_step_done"


@dataclass
class ToolCallEvent:
    tool_name: str = ""
    domain: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    seq: int = -1
    kind: Literal["tool_call"] = "tool_call"


@dataclass
class ToolResultEvent:
    tool_name: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    seq: int = -1
    kind: Literal["tool_result"] = "tool_result"


@dataclass
class FoldedEvent:
    seqs: list[int] = field(default_factory=list)
    rule_summaries: list[str] = field(default_factory=list)
    kind: Literal["folded"] = "folded"


@dataclass
class NotebookUpdateEvent:
    notebook: str = ""
    covered_count: int = 0
    kind: Literal["notebook"] = "notebook"


@dataclass
class RAGRetrievalEvent:
    results: list[dict] = field(default_factory=list)
    kind: Literal["rag"] = "rag"


@dataclass
class TokenStatsEvent:
    iteration: int = 0
    raw_tokens: int = 0
    sent_tokens: int = 0
    kind: Literal["token_stats"] = "token_stats"


@dataclass
class ConclusionEvent:
    business_impact: str = ""
    root_cause: str = ""
    actions: list[str] = field(default_factory=list)
    kind: Literal["conclusion"] = "conclusion"


@dataclass
class ErrorEvent:
    message: str = ""
    kind: Literal["error"] = "error"


@dataclass
class DoneEvent:
    reason: str = ""
    kind: Literal["done"] = "done"


Event = (
    ThoughtEvent | PlanEvent | PlanStepDoneEvent | ToolCallEvent | ToolResultEvent
    | FoldedEvent | NotebookUpdateEvent | RAGRetrievalEvent | TokenStatsEvent
    | ConclusionEvent | ErrorEvent | DoneEvent
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    return (PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")


def _estimate_tokens(messages: list[ChatMessage]) -> int:
    """Rough char/4 estimate over neutral ChatMessage list."""
    total = 0
    for m in messages:
        if m.text:
            total += len(m.text)
        for fc in m.function_calls:
            total += len(fc.name)
            total += len(json.dumps(fc.args, ensure_ascii=False))
        for fr in m.function_responses:
            total += len(fr.name)
            total += len(json.dumps(fr.response, ensure_ascii=False))
    return total // 4


# ---------------------------------------------------------------------------
# Rule-based pre-pass
# ---------------------------------------------------------------------------

def _truncate(s: str, n: int = 100) -> str:
    s = str(s).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


def rule_summary(tool_name: str, args: dict[str, Any], result: dict[str, Any]) -> str:
    args_str = ", ".join(f"{k}={v}" for k, v in args.items()) if args else ""
    head = f"[{tool_name}({args_str})]"

    if not isinstance(result, dict):
        return f"{head} {_truncate(result, 80)}"

    if result.get("status") == "no_data":
        return f"{head} 無相關資料"

    summary = result.get("summary", "")
    data = result.get("data", "")
    note = result.get("note", "")

    if isinstance(data, dict):
        flagged = [(k, v) for k, v in data.items()
                   if any(t in str(v) for t in ("⚠️", "異常", "fail", "FAIL"))]
        pick = flagged[:3] if flagged else list(data.items())[:3]
        data_str = "; ".join(f"{k}={v}" for k, v in pick)
    else:
        data_str = str(data)

    parts = [p for p in [summary, _truncate(data_str, 160), _truncate(note, 80)] if p]
    body = " | ".join(parts)
    return f"{head} {body}"


# ---------------------------------------------------------------------------
# Rolling notebook
# ---------------------------------------------------------------------------

@dataclass
class _NotebookState:
    summary: str = ""
    covered_count: int = 0


def _generate_notebook(
    provider: LLMProvider,
    incident: str,
    prior_notebook: str,
    new_entries: list[str],
) -> str:
    prompt = NOTEBOOK_PROMPT.format(
        incident=incident,
        prior_notebook=prior_notebook if prior_notebook else "（這是第一次建立）",
        new_entries="\n".join(f"- {e}" for e in new_entries),
    )
    try:
        text = provider.complete_text(
            prompt=prompt,
            temperature=0.2,
            max_output_tokens=800,
        )
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("markdown"):
                text = text[len("markdown"):].lstrip()
        return text or prior_notebook
    except Exception:
        fallback = (prior_notebook or "## 🔍 已查到什麼\n## 💡 目前推論\n資料不足\n## ❓ 還需驗證\n## 🚫 已排除\n")
        for entry in new_entries:
            fallback = fallback.replace(
                "## 💡 目前推論",
                f"- {entry}\n\n## 💡 目前推論",
                1,
            )
        return fallback


# ---------------------------------------------------------------------------
# Tool record bookkeeping
# ---------------------------------------------------------------------------

@dataclass
class _ToolRecord:
    seq: int
    tool_name: str
    args: dict[str, Any]
    raw_result: dict[str, Any]
    message_idx: int  # index in messages list (the user-role message holding the function_response)


def _build_send_messages(
    messages: list[ChatMessage],
    tool_records: list[_ToolRecord],
    notebook: _NotebookState,
    compression_enabled: bool,
    head_count: int = 1,
) -> list[ChatMessage]:
    """Hermes-style drop-middle compression on the neutral message list."""
    if not compression_enabled or notebook.covered_count == 0 or not notebook.summary:
        return list(messages)

    cut = notebook.covered_count
    if cut <= 0 or cut > len(tool_records):
        return list(messages)
    if len(tool_records) <= KEEP_RECENT_TOOL_RESPONSES:
        return list(messages)

    fresh_first = tool_records[cut]
    # function_call lives in the message just BEFORE the function_response message
    keep_from_idx = fresh_first.message_idx - 1
    if keep_from_idx <= head_count:
        return list(messages)

    out: list[ChatMessage] = list(messages[:head_count])
    out.append(ChatMessage(
        role="user",
        text=f"{CONTEXT_COMPACTION_PREAMBLE}\n\n{notebook.summary}",
    ))
    out.extend(messages[keep_from_idx:])

    if _estimate_tokens(out) >= _estimate_tokens(messages):
        return list(messages)

    return out


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def _format_rag_context(results: list[dict]) -> str:
    if not results:
        return ""
    lines = [
        "[歷史相似案例 — 來自公司過去事故 / 維修紀錄 RAG 檢索]",
        "下列是與當前事故症狀最相似的歷史紀錄，請參考但不要照抄結論，"
        "仍須依照當前實際資料判斷。",
        "",
    ]
    for i, doc in enumerate(results, 1):
        lines.append(
            f"{i}. [{doc['id']}] ({doc['date']}) · 相似度 {doc['score']*100:.0f}%"
        )
        lines.append(f"   📌 {doc['title']}")
        lines.append(f"   🚨 症狀：{doc.get('symptom', '')}")
        lines.append(f"   🎯 根因：{doc.get('root_cause', '')}")
        lines.append(f"   ✅ 解法：{doc.get('fix', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def run_agent(
    scenario: Any,
    api_key: str,
    model: str,
    max_iterations: int,
    on_event: Callable[[Event], None],
    compression_enabled: bool = True,
    enable_rag: bool = True,
) -> None:
    try:
        scenario_dict = resolve_scenario(scenario)
    except FileNotFoundError:
        on_event(ErrorEvent(message=f"找不到場景：{scenario}"))
        on_event(DoneEvent(reason="error"))
        return

    try:
        provider = make_provider(model=model, api_key=api_key)
    except Exception as e:
        on_event(ErrorEvent(message=f"LLM provider 初始化失敗：{e}"))
        on_event(DoneEvent(reason="error"))
        return

    tools_specs: list[ToolSpec] = build_function_declarations()
    system_prompt = _load_system_prompt()
    incident = scenario_dict["incident_message"]

    messages: list[ChatMessage] = [ChatMessage(role="user", text=incident)]
    head_count = 1

    # ---------- RAG retrieval ----------
    if enable_rag:
        try:
            rag_hits = rag.search(query=incident, provider=provider, top_k=3, min_score=0.55)
        except Exception as e:
            on_event(ErrorEvent(message=f"RAG 檢索失敗（不影響主流程）：{e}"))
            rag_hits = []
        on_event(RAGRetrievalEvent(results=rag_hits))
        rag_text = _format_rag_context(rag_hits)
        if rag_text:
            messages.append(ChatMessage(role="user", text=rag_text))
            head_count = 2

    tool_records: list[_ToolRecord] = []
    notebook = _NotebookState()

    plan_submitted = False
    concluded = False

    for iteration in range(max_iterations + 2):
        # ---------- Fold aged records into notebook ----------
        if compression_enabled:
            cutoff = max(0, len(tool_records) - KEEP_RECENT_TOOL_RESPONSES)
            if cutoff > notebook.covered_count:
                new_records = tool_records[notebook.covered_count:cutoff]
                rule_lines = [
                    rule_summary(r.tool_name, r.args, r.raw_result) for r in new_records
                ]
                on_event(FoldedEvent(
                    seqs=[r.seq for r in new_records],
                    rule_summaries=rule_lines,
                ))
                new_summary = _generate_notebook(
                    provider=provider,
                    incident=incident,
                    prior_notebook=notebook.summary,
                    new_entries=rule_lines,
                )
                notebook.summary = new_summary
                notebook.covered_count = cutoff
                on_event(NotebookUpdateEvent(
                    notebook=new_summary,
                    covered_count=cutoff,
                ))

        # ---------- Build send messages + token stats ----------
        send_messages = _build_send_messages(
            messages, tool_records, notebook, compression_enabled, head_count=head_count,
        )
        raw_tok = _estimate_tokens(messages)
        sent_tok = _estimate_tokens(send_messages)
        on_event(TokenStatsEvent(iteration=iteration, raw_tokens=raw_tok, sent_tokens=sent_tok))

        # ---------- Main provider call ----------
        try:
            response = provider.chat(
                messages=send_messages,
                tools=tools_specs,
                system_instruction=system_prompt,
                model=model,
                temperature=0.3,
            )
        except Exception as e:
            on_event(ErrorEvent(message=f"LLM API 錯誤 (iter {iteration + 1})：{e}"))
            on_event(DoneEvent(reason="error"))
            return

        # Mirror provider response into the neutral history
        if response.text:
            on_event(ThoughtEvent(text=response.text))
        if response.text or response.function_calls:
            messages.append(ChatMessage(
                role="assistant",
                text=response.text or None,
                function_calls=list(response.function_calls),
            ))

        if not response.function_calls:
            on_event(ThoughtEvent(text="（系統提示：請繼續呼叫工具或 submit_conclusion）"))
            nudge = (
                "請呼叫 submit_plan 提交調查計畫" if not plan_submitted
                else "請繼續呼叫工具調查，或在掌握根因時呼叫 submit_conclusion 結束。"
            )
            messages.append(ChatMessage(role="user", text=nudge))
            continue

        function_responses: list[FunctionResponse] = []
        local_tool_results: list[tuple[str, dict, dict]] = []

        for fc in response.function_calls:
            tool_name = fc.name
            args = dict(fc.args) if fc.args else {}

            if tool_name == "submit_plan":
                steps = args.get("steps", [])
                normalized_steps: list[dict[str, str]] = []
                for s in steps:
                    if isinstance(s, dict):
                        normalized_steps.append({
                            "hypothesis": str(s.get("hypothesis", "")),
                            "action": str(s.get("action", "")),
                        })
                on_event(PlanEvent(steps=normalized_steps))
                plan_submitted = True
                function_responses.append(FunctionResponse(
                    name=tool_name,
                    response={"status": "plan_received", "step_count": len(normalized_steps)},
                    call_id=fc.id,
                ))
                continue

            if tool_name == "mark_plan_step_done":
                step_index = int(args.get("step_index", 0))
                finding = str(args.get("finding", ""))
                on_event(PlanStepDoneEvent(step_index=step_index, finding=finding))
                function_responses.append(FunctionResponse(
                    name=tool_name,
                    response={"status": "marked", "step_index": step_index},
                    call_id=fc.id,
                ))
                continue

            if tool_name == "submit_conclusion":
                actions = args.get("actions", [])
                if isinstance(actions, str):
                    actions = [actions]
                on_event(ConclusionEvent(
                    business_impact=str(args.get("business_impact", "")),
                    root_cause=str(args.get("root_cause", "")),
                    actions=[str(a) for a in actions],
                ))
                concluded = True
                function_responses.append(FunctionResponse(
                    name=tool_name,
                    response={"status": "submitted"},
                    call_id=fc.id,
                ))
                break

            # Regular investigation tool
            seq = len(tool_records)
            domain = TOOL_DOMAIN.get(tool_name, "META")
            on_event(ToolCallEvent(tool_name=tool_name, domain=domain, args=args, seq=seq))
            result = dispatch_tool(scenario_dict, tool_name, args)
            on_event(ToolResultEvent(tool_name=tool_name, result=result, seq=seq))
            function_responses.append(FunctionResponse(
                name=tool_name,
                response={"result": result},
                call_id=fc.id,
            ))
            local_tool_results.append((tool_name, args, result))

        if concluded:
            on_event(DoneEvent(reason="concluded"))
            return

        # Append the tool_response message
        message_idx = len(messages)
        messages.append(ChatMessage(role="tool_response", function_responses=function_responses))
        for tn, ar, res in local_tool_results:
            tool_records.append(_ToolRecord(
                seq=len(tool_records),
                tool_name=tn,
                args=ar,
                raw_result=res,
                message_idx=message_idx,
            ))

    on_event(ConclusionEvent(
        business_impact="（達到分析步驟上限，僅提供階段性結論）",
        root_cause=f"Agent 在 {max_iterations} 輪內未找到明確根因。建議由人類工程師接手。",
        actions=["將上述調查紀錄轉交對應 IT / OT 工程師", "可調高最大步驟數重試"],
    ))
    on_event(DoneEvent(reason="max_iterations"))
