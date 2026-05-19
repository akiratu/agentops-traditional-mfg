"""Thin wrapper around the Langfuse Python SDK.

We isolate the SDK behind a stable surface so:
- Tests can inject a MagicMock instead of hitting a real Langfuse
- Upgrading Langfuse (e.g. v2 → v3 SDK changes) only requires touching this file
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from agentops_core.config import Settings


@dataclass
class LangfuseTraceClient:
    host: str
    public_key: str
    secret_key: str
    sdk_client: Any = field(default=None)  # langfuse.Langfuse instance or test mock

    @classmethod
    def from_settings(cls, settings: Settings) -> LangfuseTraceClient:
        sdk = None
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse

                sdk = Langfuse(
                    host=settings.langfuse_host,
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                )
            except ImportError:
                sdk = None
        return cls(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            sdk_client=sdk,
        )

    def is_available(self) -> bool:
        return (
            self.sdk_client is not None
            and bool(self.public_key)
            and bool(self.secret_key)
        )

    def fetch_trace(self, trace_id: str) -> dict[str, Any]:
        """Return a normalized trace dict.

        Normalized shape (independent of SDK version):
        {
          "id": str,
          "name": str,
          "input": Any,
          "output": Any,
          "observations": list[dict],
          "metadata": dict,
        }
        """
        if not self.sdk_client:
            raise RuntimeError("Langfuse SDK not initialized; check keys")
        resp = self.sdk_client.fetch_trace(trace_id)
        d = resp.data
        return {
            "id": d.id,
            "name": getattr(d, "name", None),
            "input": getattr(d, "input", None),
            "output": getattr(d, "output", None),
            "observations": [
                self._obs_to_dict(o) for o in getattr(d, "observations", []) or []
            ],
            "metadata": getattr(d, "metadata", {}) or {},
        }

    def search_traces(
        self,
        *,
        agent_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        only_failures: bool = False,
    ) -> list[dict[str, Any]]:
        """Return a list of trace summary dicts.

        Summary shape:
        {"id": str, "name": str, "timestamp": str (ISO), "metadata": dict}
        """
        if not self.sdk_client:
            raise RuntimeError("Langfuse SDK not initialized; check keys")
        # Langfuse 2.x: fetch_traces accepts various kwargs. We pass a conservative
        # subset; richer filtering (only_failures via scores) lives in caller code.
        kwargs: dict[str, Any] = {"limit": limit}
        if agent_id:
            # We tag traces with metadata.agent_id when emitting from our runtime.
            kwargs["user_id"] = (
                agent_id  # langfuse v2: user_id is the conventional bucket
            )
        if since:
            kwargs["from_timestamp"] = since
        if until:
            kwargs["to_timestamp"] = until
        resp = self.sdk_client.fetch_traces(**kwargs)
        return [
            {
                "id": t.id,
                "name": getattr(t, "name", None),
                "timestamp": (
                    getattr(t, "timestamp", None).isoformat()
                    if getattr(t, "timestamp", None)
                    else None
                ),
                "metadata": getattr(t, "metadata", {}) or {},
            }
            for t in (resp.data or [])
        ]

    @staticmethod
    def _obs_to_dict(o: Any) -> dict[str, Any]:
        return {
            "id": getattr(o, "id", None),
            "type": getattr(o, "type", None),
            "name": getattr(o, "name", None),
            "input": getattr(o, "input", None),
            "output": getattr(o, "output", None),
            "start_time": (
                getattr(o, "start_time", None).isoformat()
                if getattr(o, "start_time", None)
                else None
            ),
        }
