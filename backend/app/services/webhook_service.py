import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.event import Event
from app.services.event_processor import process_event
from app.schemas.webhook import ParsedWebhookEvent

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def persist_event(db: Session, parsed: ParsedWebhookEvent) -> tuple[Event | None, bool]:
    """
    Persist a webhook event.

    Returns (event, is_new). On duplicate event_id the session is rolled back
    and (None, False) is returned — the database UNIQUE constraint is authoritative.
    """
    event = Event(
        event_id=parsed.event_id,
        event_type=parsed.event_type,
        comment_id=parsed.comment_id,
        post_id=parsed.post_id,
        user_id=parsed.user_id,
        username=parsed.username,
        text=parsed.text,
        payload=parsed.payload,
        sent_at=parsed.sent_at,
        received_at=_utc_now(),
        processed=False,
    )
    db.add(event)
    try:
        db.commit()
        db.refresh(event)
        return event, True
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_event_error(exc):
            logger.info(
                "Duplicate webhook event ignored: event_id=%s",
                parsed.event_id,
            )
            return None, False
        raise


def _is_duplicate_event_error(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower() if exc.orig else str(exc).lower()
    is_unique_violation = "unique" in message or "duplicate" in message
    return is_unique_violation and "event_id" in message


def schedule_event_processing(event_id: str) -> None:
    """Run durable event processing in a fresh session after acknowledgement."""
    db = SessionLocal()
    try:
        process_event(db, event_id)
    finally:
        db.close()
