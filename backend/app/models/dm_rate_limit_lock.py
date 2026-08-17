from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DMRateLimitLock(Base):
    """Singleton row used to serialize durable rolling-window reservations."""

    __tablename__ = "dm_rate_limit_lock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
