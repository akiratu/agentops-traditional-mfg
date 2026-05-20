from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session as SASession
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class TimestampedModel(SQLModel):
    """Mixin: every entity carries id + created_at + updated_at.

    updated_at is refreshed automatically before every flush that
    touches a dirty TimestampedModel instance, via a SQLAlchemy
    before_flush session event registered at class-definition time.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=_utcnow, nullable=False)


@event.listens_for(SASession, "before_flush")
def _refresh_updated_at(
    session: SASession, flush_context, instances
) -> None:  # noqa: ARG001
    for obj in session.dirty:
        if isinstance(obj, TimestampedModel):
            obj.updated_at = _utcnow()
