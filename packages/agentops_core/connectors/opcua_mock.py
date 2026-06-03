"""Mock OT connector (OPC-UA style) for AgentOps PoC.

This is a *placeholder* implementation that simulates reading CNC machine
sensor data — temperature, vibration, spindle RPM — so the Trace Analyzer
ReAct loop can demonstrate "querying live OT data" during demos.

In production, replace this module with a real OPC-UA client (e.g.
``opcua-client`` or ``asyncua``) connected to the factory's SCADA/MES.

Design:
- Each ``MachineNode`` holds a sliding window of recent readings.
- ``read_machine_data(machine_id, metric, minutes)`` returns time-series
  suitable for LLM tool-call consumption (short JSON).
- A FastAPI endpoint ``GET /ot/machines/{machine_id}`` exposes the same
  data over HTTP for the UI or external agents.
"""

from __future__ import annotations

import logging
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class MachineReading:
    ts: datetime
    temperature_c: float   # °C
    vibration_mm_s: float  # mm/s RMS
    spindle_rpm: int


@dataclass
class MachineNode:
    machine_id: str
    history: deque[MachineReading] = field(default_factory=lambda: deque(maxlen=500))

    def push(self, reading: MachineReading) -> None:
        self.history.append(reading)

    def query(
        self,
        metric: str | None = None,
        minutes: int = 60,
    ) -> dict[str, Any]:
        """Return recent readings in a LLM-friendly JSON shape."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent = [r for r in self.history if r.ts >= cutoff]
        if metric:
            key = {
                "temperature": "temperature_c",
                "vibration": "vibration_mm_s",
                "rpm": "spindle_rpm",
            }.get(metric, metric)
            series = [
                {"ts": r.ts.isoformat(), "value": getattr(r, key)}
                for r in recent
            ]
            return {
                "machine_id": self.machine_id,
                "metric": metric,
                "minutes": minutes,
                "count": len(series),
                "latest": series[-1] if series else None,
                "series": series,
            }
        # Full snapshot
        return {
            "machine_id": self.machine_id,
            "minutes": minutes,
            "count": len(recent),
            "latest": {
                "ts": recent[-1].ts.isoformat(),
                "temperature_c": recent[-1].temperature_c,
                "vibration_mm_s": recent[-1].vibration_mm_s,
                "spindle_rpm": recent[-1].spindle_rpm,
            }
            if recent
            else None,
            "series": [
                {
                    "ts": r.ts.isoformat(),
                    "temperature_c": r.temperature_c,
                    "vibration_mm_s": r.vibration_mm_s,
                    "spindle_rpm": r.spindle_rpm,
                }
                for r in recent
            ],
        }


# In-memory store (single-process demo)
_MACHINES: dict[str, MachineNode] = {}


def get_or_create_machine(machine_id: str) -> MachineNode:
    if machine_id not in _MACHINES:
        _MACHINES[machine_id] = MachineNode(machine_id)
    return _MACHINES[machine_id]


def seed_mock_data(machine_id: str, hours: int = 24) -> None:
    """Pre-fill a machine with synthetic drift data (for demo / unit tests)."""
    node = get_or_create_machine(machine_id)
    now = datetime.utcnow()
    base_temp = 45.0
    base_vib = 2.0
    base_rpm = 8000
    for m in range(hours * 60):
        # Gradual drift + small noise
        drift = m * 0.02
        noise_t = random.gauss(0, 0.5)
        noise_v = random.gauss(0, 0.1)
        r = MachineReading(
            ts=now - timedelta(minutes=hours * 60 - m),
            temperature_c=round(base_temp + drift + noise_t, 2),
            vibration_mm_s=round(base_vib + drift * 0.05 + noise_v, 3),
            spindle_rpm=int(base_rpm + random.gauss(0, 50)),
        )
        node.push(r)
    log.info("Seeded %d mock readings for machine %s", hours * 60, machine_id)


def read_machine_data(
    machine_id: str,
    metric: str | None = None,
    minutes: int = 60,
) -> dict[str, Any]:
    """Primary callable — used by Trace Analyzer tool registry."""
    node = get_or_create_machine(machine_id)
    # If empty, auto-seed 1 hour so the tool never returns null on first call.
    if not node.history:
        seed_mock_data(machine_id, hours=1)
    return node.query(metric=metric, minutes=minutes)
