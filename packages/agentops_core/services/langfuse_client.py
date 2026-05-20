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

        When ``only_failures=True``, keeps only traces with a score named
        ``rca_accuracy`` (or any score whose value is < 0.5). A trace
        without any scores is treated as "unknown" and excluded.

        Summary shape:
        {"id": str, "name": str, "timestamp": str (ISO), "metadata": dict,
         "scores": list[dict]}
        """
        if not self.sdk_client:
            raise RuntimeError("Langfuse SDK not initialized; check keys")
        kwargs: dict[str, Any] = {"limit": limit}
        if agent_id:
            kwargs["user_id"] = agent_id
        if since:
            kwargs["from_timestamp"] = since
        if until:
            kwargs["to_timestamp"] = until
        resp = self.sdk_client.fetch_traces(**kwargs)

        summaries: list[dict[str, Any]] = []
        for t in resp.data or []:
            scores = list(getattr(t, "scores", []) or [])
            scores_dicts = [self._score_to_dict(s) for s in scores]
            if only_failures and not self._is_failure(scores_dicts):
                continue
            summaries.append(
                {
                    "id": t.id,
                    "name": getattr(t, "name", None),
                    "timestamp": getattr(t, "timestamp", None).isoformat()
                    if getattr(t, "timestamp", None)
                    else None,
                    "metadata": getattr(t, "metadata", {}) or {},
                    "scores": scores_dicts,
                }
            )
        return summaries

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

    @staticmethod
    def _score_to_dict(score: Any) -> dict[str, Any]:
        if isinstance(score, dict):
            return {"name": score.get("name"), "value": score.get("value")}
        return {"name": getattr(score, "name", None), "value": getattr(score, "value", None)}

    @staticmethod
    def _is_failure(scores: list[dict[str, Any]]) -> bool:
        """A trace is a failure if any score has value < 0.5.

        Convention: success scores live in [0, 1] (Langfuse convention),
        with 1.0 = perfect match and 0.0 = total miss. The 0.5 boundary
        treats "partial" (e.g. 0.4) as a failure-side signal, since
        partial misses are exactly what Self-Evolve should learn from.
        """
        for s in scores:
            v = s.get("value")
            if isinstance(v, (int, float)) and v < 0.5:
                return True
        return False
