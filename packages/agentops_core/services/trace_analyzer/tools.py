"""Langfuse query tools the Trace Analyzer agent calls.

Each tool has:
- An OpenAI-style function schema (the LLM uses this to know how/when to call)
- A Python callable that takes (langfuse_client, **args) and returns a dict/list

Schemas use the openai tool-calling format so the agent loop can pass them
straight to chat.completions.create(tools=...).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from agentops_core.services.langfuse_client import LangfuseTraceClient


def search_traces_tool(
    client: LangfuseTraceClient,
    *,
    agent_id: str | None = None,
    since: datetime | None = None,
    limit: int = 20,
    only_failures: bool = False,
) -> list[dict[str, Any]]:
    """List recent traces for an agent (default: 20 most recent)."""
    return client.search_traces(
        agent_id=agent_id, since=since, limit=limit, only_failures=only_failures
    )


def fetch_trace_detail_tool(
    client: LangfuseTraceClient, *, trace_id: str
) -> dict[str, Any]:
    """Fetch full trace: input, output, all LLM/tool observations."""
    return client.fetch_trace(trace_id)


LANGFUSE_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_traces",
            "description": (
                "List recent Langfuse traces for an agent. Use this first to discover "
                "which traces look anomalous. Returns a list of {id, name, timestamp, metadata}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent UUID to scope the search to.",
                    },
                    "since_iso": {
                        "type": "string",
                        "description": "Optional ISO-8601 lower bound for trace timestamps.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of traces (default 20, max 100).",
                        "default": 20,
                    },
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_trace_detail",
            "description": (
                "Get the full content of one trace: input, output, and every LLM / tool span. "
                "Call this on a trace_id you got from search_traces to dig in."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {
                        "type": "string",
                        "description": "The Langfuse trace ID.",
                    }
                },
                "required": ["trace_id"],
            },
        },
    },
]
