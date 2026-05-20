import time
from unittest.mock import MagicMock

from agentops_core.services.scheduler import (
    build_scheduler,
    start_scheduler,
    stop_scheduler,
)


def test_build_scheduler_registers_job():
    fake_runner = MagicMock(__name__="run_anomaly_check")
    sched = build_scheduler(
        anomaly_check_runner=fake_runner,
        interval_seconds=3600,
    )
    job_ids = {j.id for j in sched.get_jobs()}
    assert "anomaly_check" in job_ids


def test_start_and_stop_scheduler_idempotent():
    sched = build_scheduler(
        anomaly_check_runner=lambda: None,
        interval_seconds=3600,
    )
    start_scheduler(sched)
    assert sched.running is True
    start_scheduler(sched)
    assert sched.running is True
    stop_scheduler(sched)
    assert sched.running is False
    stop_scheduler(sched)


def test_job_actually_fires_with_short_interval():
    counter = {"calls": 0}

    def fake_runner():
        counter["calls"] += 1

    sched = build_scheduler(
        anomaly_check_runner=fake_runner,
        interval_seconds=1,
    )
    start_scheduler(sched)
    try:
        for _ in range(30):
            if counter["calls"] >= 1:
                break
            time.sleep(0.1)
    finally:
        stop_scheduler(sched)

    assert counter["calls"] >= 1
