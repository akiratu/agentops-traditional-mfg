"""Seed synthetic Langfuse traces for the Trace Analyzer demo.

Pushes 5 traces for the CTIS RCA Agent simulating a "diagnostic accuracy
dropped due to new vendor X probe card" pattern: 2 successful (old vendor),
3 failed (new vendor X, agent gave generic answer).

Usage:
    cd /Users/akiratu/Downloads/claude\ code/agentops-traditional-mfg
    source .venv/bin/activate
    python scripts/seed_demo_traces.py

Reads LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY from .env.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from langfuse import Langfuse

from agentops_core.config import get_settings


AGENT_ID = "650b0a4c-b29e-4f1f-a940-312c85e281e7"  # CTIS RCA Agent


def make_lf() -> Langfuse:
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        print(
            "ERROR: LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set in .env",
            file=sys.stderr,
        )
        sys.exit(1)
    return Langfuse(
        host=s.langfuse_host,
        public_key=s.langfuse_public_key,
        secret_key=s.langfuse_secret_key,
    )


def main() -> list[str]:
    lf = make_lf()
    trace_ids: list[str] = []

    base_ts = datetime.now(tz=timezone.utc) - timedelta(days=2)

    fixtures = [
        # 2 successes (vendor A probe card — covered by SOP)
        {
            "name": "rca_session_ok_1",
            "ts": base_ts + timedelta(hours=1),
            "input": {"query": "Tester #5 yield 從 95% 掉到 82%,vendor A probe card"},
            "output": {
                "root_cause": "Probe card 接觸電阻上升超過閾值,建議更換",
                "verdict": "match",
            },
            "score": 1.0,
        },
        {
            "name": "rca_session_ok_2",
            "ts": base_ts + timedelta(hours=3),
            "input": {"query": "Bin 5 spike,vendor A 機台 #2"},
            "output": {
                "root_cause": "Probe card 壽命接近,touchdown count 1.9M",
                "verdict": "match",
            },
            "score": 1.0,
        },
        # 3 failures (vendor X probe card — NOT covered by SOP)
        {
            "name": "rca_session_fail_1",
            "ts": base_ts + timedelta(hours=10),
            "input": {
                "query": "Tester #7 yield 突然從 92% 掉到 71%,新進的 vendor X probe card"
            },
            "output": {
                "root_cause": "(資料不足)無法確認根因,建議聯絡製造部",
                "verdict": "miss",
            },
            "score": 0.0,
        },
        {
            "name": "rca_session_fail_2",
            "ts": base_ts + timedelta(hours=14),
            "input": {
                "query": "vendor X probe card 上機後 Bin 5 集中在 Tester #7"
            },
            "output": {
                "root_cause": "可能是 wafer 問題?需要更多資料",
                "verdict": "miss",
            },
            "score": 0.0,
        },
        {
            "name": "rca_session_fail_3",
            "ts": base_ts + timedelta(hours=22),
            "input": {
                "query": "新廠商 X 的 probe card firmware 版本是 v3.2,跟舊的不同,yield 異常"
            },
            "output": {
                "root_cause": "(LLM unavailable)",
                "verdict": "miss",
            },
            "score": 0.0,
        },
    ]

    for fx in fixtures:
        tid = str(uuid.uuid4())
        trace = lf.trace(
            id=tid,
            name=fx["name"],
            user_id=AGENT_ID,
            input=fx["input"],
            output=fx["output"],
            metadata={
                "agent_id": AGENT_ID,
                "skill_version": 11,
                "synthetic": True,
            },
            timestamp=fx["ts"],
        )
        # Add an evaluation score (success/failure signal)
        lf.score(
            trace_id=tid,
            name="rca_accuracy",
            value=fx["score"],
            comment=("ground truth match" if fx["score"] >= 0.5 else "miss"),
        )
        trace_ids.append(tid)
        print(f"  seeded {fx['name']}: trace_id={tid[:8]}... score={fx['score']}")

    lf.flush()
    time.sleep(1)  # let Langfuse settle

    print(f"\nDone. {len(trace_ids)} traces pushed for agent_id={AGENT_ID}.")
    print(f"\nFailed trace IDs (use for AnomalySignal):")
    for tid in trace_ids[2:]:  # last 3 are failures
        print(f"  {tid}")

    return trace_ids


if __name__ == "__main__":
    main()
