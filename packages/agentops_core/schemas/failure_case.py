"""FailureCase schema — contract between Trace Analyzer (Plan 3) and Self-Evolve.

We re-export flows2agents.evolve.models.FailureCase so callers in agentops_core
don't take a direct dependency on flows2agents internals. If the upstream contract
changes, this module is the single place to adapt.
"""
from __future__ import annotations

from flows2agents.evolve.models import FailureCase

__all__ = ["FailureCase"]
