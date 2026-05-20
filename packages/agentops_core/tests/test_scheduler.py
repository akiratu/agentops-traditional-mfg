import time
from unittest.mock import MagicMock

from agentops_core.services.scheduler import build_scheduler, start_scheduler, stop_scheduler


def test_build_scheduler_registers_jobs():
    fake_metric = MagicMock(__name__="run_metric_drift")
    fake_cost = MagicMock(__name__="run_cost_spike")
    sched = build_scheduler(
        metric_drift_runner=fake_metric,
        cost_spike_runner=fake_cost,
        metric_interval_seconds=3600,
        cost_interval_seconds=3600,
    )
    job_ids = {j.id for j in sched.get_jobs()}
    assert "metric_drift" in job_ids
    assert "cost_spike" in job_ids


def test_start_and_stop_scheduler_idempotent():
    sched = build_scheduler(
        metric_drift_runner=lambda: None,
        cost_spike_runner=lambda: None,
        metric_interval_seconds=3600,
        cost_interval_seconds=3600,
    )
    start_scheduler(sched)
    assert sched.running is True
    start_scheduler(sched)
    assert sched.running is True
    stop_scheduler(sched)
    assert sched.running is False
    stop_scheduler(sched)


def test_jobs_actually_fire_with_short_interval():
    counter = {"metric": 0, "cost": 0}

    def fake_metric():
        counter["metric"] += 1

    def fake_cost():
        counter["cost"] += 1

    sched = build_scheduler(
        metric_drift_runner=fake_metric,
        cost_spike_runner=fake_cost,
        metric_interval_seconds=1,
        cost_interval_seconds=1,
    )
    start_scheduler(sched)
    try:
        for _ in range(30):
            if counter["metric"] >= 1 and counter["cost"] >= 1:
                break
            time.sleep(0.1)
    finally:
        stop_scheduler(sched)

    assert counter["metric"] >= 1
    assert counter["cost"] >= 1
