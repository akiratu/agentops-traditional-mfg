"""APScheduler wrapper for anomaly-detection jobs.

We keep this module thin and dependency-free of the detectors themselves —
detectors are passed in as callables so tests can substitute mocks and the
main() module can wire in real ones.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)


def build_scheduler(
    *,
    metric_drift_runner: Callable[[], None],
    cost_spike_runner: Callable[[], None],
    metric_interval_seconds: int = 3600,
    cost_interval_seconds: int = 3600,
) -> BackgroundScheduler:
    """Return an unstarted BackgroundScheduler with both jobs registered."""
    sched = BackgroundScheduler(
        timezone="UTC",
        job_defaults={"coalesce": True, "max_instances": 1},
    )
    sched.add_job(
        metric_drift_runner,
        trigger="interval",
        seconds=metric_interval_seconds,
        id="metric_drift",
        next_run_time=None,
    )
    sched.add_job(
        cost_spike_runner,
        trigger="interval",
        seconds=cost_interval_seconds,
        id="cost_spike",
        next_run_time=None,
    )
    return sched


def start_scheduler(sched: BackgroundScheduler) -> None:
    if sched.running:
        return
    from datetime import datetime

    now = datetime.now(tz=UTC)
    for job in sched.get_jobs():
        sched.modify_job(job.id, next_run_time=now)
    sched.start()
    log.info("Scheduler started; jobs: %s", [j.id for j in sched.get_jobs()])


def stop_scheduler(sched: BackgroundScheduler) -> None:
    if not sched.running:
        return
    sched.shutdown(wait=False)
    log.info("Scheduler stopped")
