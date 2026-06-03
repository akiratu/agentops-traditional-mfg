"""DB query tools the Trace Analyzer agent calls.

These read from our application DB to give the analyzer context about
the agent under investigation: its current skill, version history, and
similar past findings.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from agentops_core.models.anomaly_signal import AnomalySignal
from agentops_core.models.rca_finding import RCAFinding
from agentops_core.models.skill import Skill
from agentops_core.models.agent import Agent


def fetch_skill_detail_tool(
    session: Session, *, skill_id: UUID
) -> dict[str, Any] | None:
    skill = session.get(Skill, skill_id)
    if skill is None:
        return None
    return {
        "id": str(skill.id),
        "agent_id": str(skill.agent_id),
        "version": skill.version,
        "status": (
            skill.status.value if hasattr(skill.status, "value") else str(skill.status)
        ),
        "prompt": skill.prompt,
        "tool_specs": skill.tool_specs,
        "golden_test_cases": skill.golden_test_cases,
        "sop_source_set_id": skill.sop_source_set_id,
        "generated_by_run_id": skill.generated_by_run_id,
    }


def fetch_skill_versions_tool(
    session: Session, *, agent_id: UUID
) -> list[dict[str, Any]]:
    skills = list(session.exec(select(Skill).where(Skill.agent_id == agent_id)).all())
    return [
        {
            "id": str(s.id),
            "version": s.version,
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "sop_source_set_id": s.sop_source_set_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "prompt_excerpt": (s.prompt or "")[:200],
        }
        for s in skills
    ]


def fetch_past_findings_tool(
    session: Session, *, agent_id: UUID, k: int = 3
) -> list[dict[str, Any]]:
    """Top-k recent RCA findings for this agent (newest first).

    v0.1 uses recency as the similarity proxy. v0.2 can add embedding-based
    semantic similarity to the current signal's traces.
    """
    stmt = (
        select(RCAFinding, AnomalySignal)
        .join(AnomalySignal, RCAFinding.anomaly_signal_id == AnomalySignal.id)
        .where(AnomalySignal.agent_id == agent_id)
        .order_by(RCAFinding.created_at.desc())
        .limit(k)
    )
    rows = list(session.exec(stmt).all())
    return [
        {
            "finding_id": str(f.id),
            "anomaly_signal_id": str(f.anomaly_signal_id),
            "root_cause_summary": f.root_cause_summary,
            "suggested_fix_type": (
                f.suggested_fix_type.value
                if hasattr(f.suggested_fix_type, "value")
                else str(f.suggested_fix_type)
            ),
            "confidence_score": f.confidence_score,
            "status": f.status.value if hasattr(f.status, "value") else str(f.status),
        }
        for (f, _) in rows
    ]


def search_knowledge_base_tool(
    session: Session,
    *,
    agent_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search the per-factory RAG knowledge base for relevant SOP or past RCA cases.

    Returns a ranked list of { source, document, distance, metadata }.
    Use this to verify whether the current failure is a *known* gap already
    covered by an SOP or previously diagnosed RCA finding.
    """
    from agentops_core.connectors.rag_store import RAGStore
    from agentops_core.models.agent import Agent
    from agentops_core.models.factory import Factory

    agent = session.get(Agent, UUID(agent_id))
    if agent is None:
        return []

    factory = session.get(Factory, agent.factory_id)
    if factory is None:
        return []

    store = RAGStore(str(factory.id))
    return store.search(query, top_k=top_k, agent_id=agent_id)


DB_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "fetch_skill_detail",
            "description": (
                "Read the prompt, tool specs, and golden test cases of one Skill version. "
                "Use this to understand what behavior the agent SHOULD have."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {"type": "string", "description": "Skill UUID."},
                },
                "required": ["skill_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_skill_versions",
            "description": (
                "List all Skill versions for an agent, newest first. Useful for spotting "
                "regression-after-version-bump patterns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent UUID."},
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_past_findings",
            "description": (
                "Get the top-k most recent RCA findings for this agent. Helps you avoid "
                "duplicating analysis and to learn from accepted fixes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent UUID."},
                    "k": {"type": "integer", "default": 3},
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the factory's RAG knowledge base (SOP docs + past RCA findings) "
                "for content semantically related to the failure. "
                "Use this to check whether the current anomaly is a *known* gap "
                "already documented in SOP or previously diagnosed. "
                "Returns ranked chunks with distance scores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent UUID to scope the search."},
                    "query": {"type": "string", "description": "The failure pattern or symptom to search for (Traditional Chinese OK)."},
                    "top_k": {"type": "integer", "default": 5, "description": "Max chunks to return."},
                },
                "required": ["agent_id", "query"],
            },
        },
    },
]
