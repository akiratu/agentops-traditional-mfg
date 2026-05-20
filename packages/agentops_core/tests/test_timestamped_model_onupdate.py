import time
from datetime import timedelta

from sqlmodel import Session

from agentops_core.models.factory import Factory


def test_updated_at_changes_on_mutation(session: Session):
    f = Factory(name="F1")
    session.add(f)
    session.commit()
    session.refresh(f)
    original_updated_at = f.updated_at

    # Sleep at least 10ms so the timestamp delta is observable on systems with
    # coarser clocks. SQLite's `CURRENT_TIMESTAMP` is second-precision so we
    # need a >=1s sleep there; but our onupdate uses Python's datetime.now,
    # which is microsecond precision.
    time.sleep(0.01)

    f.name = "F1-renamed"
    session.add(f)
    session.commit()
    session.refresh(f)

    assert f.updated_at > original_updated_at
    assert f.updated_at - original_updated_at >= timedelta(milliseconds=1)
