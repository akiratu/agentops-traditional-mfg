"""Service that orchestrates: anomaly signal → Trace Analyzer agent → RCAFinding row."""
from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from sqlmodel import Session

from agentops_core.config import Settings
from agentops_core.models.agent import Agent
from agentops_core.models.anomaly_signal import AnomalySignal
from agentops_core.models.rca_finding import RCAFinding
from agentops_core.models.skill import Skill
from agentops_core.schemas import FailureCase
from agentops_core.services.langfuse_client import LangfuseTraceClient
from agentops_core.services.trace_analyzer.agent import (
    TraceAnalyzerInput,
    TraceAnalyzerOutput,
    run_trace_analyzer,
)
from agentops_core.services.trace_analyzer.db_tools import (
    fetch_past_findings_tool,
    fetch_skill_detail_tool,
    fetch_skill_versions_tool,
)
from agentops_core.services.trace_analyzer.output import build_rca_finding_payload
from agentops_core.services.trace_analyzer.tools import (
    fetch_trace_detail_tool,
    search_traces_tool,
)


def _make_openai_client(settings: Settings) -> Any:
    """Build an openai SDK client pointed at the configured provider's endpoint."""
    from openai import OpenAI

    if settings.llm_provider_name == "google" and settings.gemini_api_key:
        os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
        return OpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    if settings.llm_provider_name == "ollama":
        return OpenAI(
            api_key="ollama",  # any non-empty string works; Ollama ignores it
            base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/v1",
        )
    # Default: assume OpenAI proper (OPENAI_API_KEY in env)
    return OpenAI()


def _resolve_model(settings: Settings) -> str:
    if settings.trace_analyzer_model:
        return settings.trace_analyzer_model
    if settings.llm_provider_name == "google":
        return "gemini-2.5-pro"
    if settings.llm_provider_name == "ollama":
        return os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    return "gpt-4o-mini"


def analyze_anomaly_signal(
    *,
    anomaly_signal_id: UUID,
    session: Session,
    langfuse_client: LangfuseTraceClient,
    settings: Settings,
) -> tuple[RCAFinding, list[FailureCase]]:
    """End-to-end: load context, run analyzer, persist RCAFinding.

    Returns (saved_finding, raw_failure_cases) so the caller (API layer) can
    return both. failure_cases are NOT auto-submitted to /self-evolutions —
    a human-in-the-loop decides whether to accept the finding first.
    """
    signal = session.get(AnomalySignal, anomaly_signal_id)
    if signal is None:
        raise ValueError(f"anomaly_signal {anomaly_signal_id} not found")

    agent = session.get(Agent, signal.agent_id)
    if agent is None:
        raise ValueError(f"agent {signal.agent_id} not found (orphan signal)")

    skill_id = agent.current_skill_id
    if skill_id is None:
        raise ValueError(f"agent {agent.id} has no current_skill_id; cannot analyze")

    skill = session.get(Skill, skill_id)
    if skill is None:
        raise ValueError(f"skill {skill_id} not found")

    inputs = TraceAnalyzerInput(
        anomaly_signal_id=signal.id,
        agent_id=agent.id,
        skill_id=skill.id,
        related_trace_refs=list(signal.related_trace_refs or []),
    )

    # Wire the tool registry. Each tool gets the right dependencies bound.
    tool_registry = {
        "search_traces": lambda agent_id, limit=20, since_iso=None: search_traces_tool(
            langfuse_client, agent_id=agent_id, limit=limit
        ),
        "fetch_trace_detail": lambda trace_id: fetch_trace_detail_tool(
            langfuse_client, trace_id=trace_id
        ),
        "fetch_skill_detail": lambda skill_id: fetch_skill_detail_tool(
            session, skill_id=UUID(skill_id)
        ),
        "fetch_skill_versions": lambda agent_id: fetch_skill_versions_tool(
            session, agent_id=UUID(agent_id)
        ),
        "fetch_past_findings": lambda agent_id, k=3: fetch_past_findings_tool(
            session, agent_id=UUID(agent_id), k=k
        ),
    }

    client = _make_openai_client(settings)
    model = _resolve_model(settings)

    output: TraceAnalyzerOutput = run_trace_analyzer(
        inputs,
        openai_client=client,
        model=model,
        tool_registry=tool_registry,
        max_steps=settings.trace_analyzer_max_steps,
    )

    payload = build_rca_finding_payload(output, anomaly_signal_id=signal.id)
    finding = RCAFinding(**payload)
    session.add(finding)
    session.commit()
    session.refresh(finding)

    return finding, output.failure_cases
