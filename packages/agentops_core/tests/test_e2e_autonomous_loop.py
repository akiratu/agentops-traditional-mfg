"""End-to-end autonomous loop test (skipped by default).

The autonomous loop is:
1. APScheduler tick → detect_metric_drift sees enough Langfuse traces with
   score < 0.5 → creates AnomalySignal(source=metric_drift)
2. signal creation → orchestrator.run_trace_analyzer_for_signal → POST equivalent
   of /trace-analyses → RCAFinding(status=proposed)
3. Operator reviews → PATCH /rca-findings/{id}/status to ACCEPTED
4. accept → orchestrator.run_self_evolve_for_finding → flows2agents Self-Evolve
   → new Skill (status=draft) + RegressionRun
5. Operator reviews regression → PATCH /skills/{new_id}/status to ACTIVE
6. PATCH /agents/{id}/current-skill to new skill_id

To exercise this on a real system, set up:
- LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY (in .env)
- GEMINI_API_KEY / LLM_PROVIDER_NAME=google
- Seed a Langfuse trace with score < 0.5 for an agent
- Start uvicorn, wait an hour for the scheduler, or call
  ``orchestrator.run_anomaly_check_all_agents()`` directly from a REPL.
"""
import os

import pytest


@pytest.mark.skipif(
    not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("GEMINI_API_KEY")),
    reason="Requires real Langfuse + Gemini env for autonomous loop e2e",
)
def test_e2e_autonomous_loop():
    pytest.skip(
        "Manual verification — see test docstring for setup steps. "
        "Run with `pytest -k test_e2e_autonomous_loop`."
    )
