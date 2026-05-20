"""APScheduler wrapper for anomaly-detection jobs.

We keep this module thin and dependency-free of the detectors themselves —
the runner is passed in as a callable so tests can substitute mocks and the
main() module can wire in the real `run_anomaly_check_all_agents`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)


def build_scheduler(
    *,
    anomaly_check_runner: Callable[[], None],
    interval_seconds: int = 3600,
) -> BackgroundScheduler:
    """Return an unstarted BackgroundScheduler with the anomaly-check job."""
    sched = BackgroundScheduler(
        timezone="UTC",
        job_defaults={"coalesce": True, "max_instances": 1},
    )
    sched.add_job(
        anomaly_check_runner,
        trigger="interval",
        seconds=interval_seconds,
        id="anomaly_check",
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
