import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeliveryStatus(str, enum.Enum):
    QUEUED = "queued"
    DELIVERED = "delivered"
    FAILED = "failed"


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dm_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dm_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    dm_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(
            DeliveryStatus,
            name="delivery_status",
            native_enum=False,
            length=20,
            values_callable=lambda statuses: [s.value for s in statuses],
        ),
        nullable=False,
        default=DeliveryStatus.QUEUED,
    )
    recipient_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    __table_args__ = (
        Index("ix_deliveries_status", "status"),
        Index("ix_deliveries_dm_id", "dm_id"),
        Index("ix_deliveries_recipient_user_id", "recipient_user_id"),
    )
