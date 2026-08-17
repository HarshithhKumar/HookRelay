import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DMJobStatus(str, enum.Enum):
    QUEUED = "queued"
    SENDING = "sending"
    ACCEPTED = "accepted"
    RETRYING = "retrying"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DMJob(Base):
    __tablename__ = "dm_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    # References the webhook event_id string for traceability.
    event_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    comment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DMJobStatus] = mapped_column(
        Enum(
            DMJobStatus,
            name="dm_job_status",
            native_enum=False,
            length=20,
            values_callable=lambda statuses: [s.value for s in statuses],
        ),
        nullable=False,
        default=DMJobStatus.QUEUED,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dm_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    __table_args__ = (
        # One DM per rule per recipient — enforced at the database level.
        UniqueConstraint(
            "rule_id",
            "recipient_user_id",
            name="uq_dm_jobs_rule_recipient",
        ),
        Index("ix_dm_jobs_status", "status"),
        Index("ix_dm_jobs_next_retry_at", "next_retry_at"),
        Index("ix_dm_jobs_claimed_at", "claimed_at"),
        Index("ix_dm_jobs_recipient_user_id", "recipient_user_id"),
        Index("ix_dm_jobs_rule_id", "rule_id"),
        Index("ix_dm_jobs_event_id", "event_id"),
    )
