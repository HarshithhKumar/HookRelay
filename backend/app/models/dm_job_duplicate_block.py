import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DMJobDuplicateBlock(Base):
    """A durable record of a DM job prevented by the uniqueness constraint."""

    __tablename__ = "dm_job_duplicate_blocks"

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
    event_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    __table_args__ = (
        Index("ix_dm_job_duplicate_blocks_rule_id", "rule_id"),
        Index("ix_dm_job_duplicate_blocks_event_id", "event_id"),
        Index(
            "ix_dm_job_duplicate_blocks_recipient_user_id",
            "recipient_user_id",
        ),
    )
