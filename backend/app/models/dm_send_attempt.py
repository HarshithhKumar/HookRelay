import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DMSendAttempt(Base):
    """A durable reservation for one outbound PseudoGram POST attempt."""

    __tablename__ = "dm_send_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    dm_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dm_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )

    __table_args__ = (Index("ix_dm_send_attempts_attempted_at", "attempted_at"),)
