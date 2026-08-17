import logging
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dm_job import DMJob, DMJobStatus
from app.models.dm_job_duplicate_block import DMJobDuplicateBlock
from app.models.event import Event
from app.models.rule import Rule
from app.services.rule_matcher import matching_rules

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EventProcessingResult:
    event_found: bool
    already_processed: bool
    jobs_created: int
    duplicates_blocked: int


def process_pending_events(db: Session) -> list[EventProcessingResult]:
    """Process every event still marked as unprocessed in durable storage."""
    event_ids = [
        event_id
        for (event_id,) in db.query(Event.event_id)
        .filter(Event.processed.is_(False))
        .order_by(Event.received_at.asc())
        .all()
    ]
    return [process_event(db, event_id) for event_id in event_ids]


def process_event(db: Session, event_id: str) -> EventProcessingResult:
    """Transactionally process one persisted event into future-send DM jobs."""
    event = db.query(Event).filter(Event.event_id == event_id).one_or_none()
    if event is None:
        return EventProcessingResult(False, False, 0, 0)
    if event.processed:
        return EventProcessingResult(True, True, 0, 0)

    jobs_created = 0
    duplicates_blocked = 0
    try:
        if event.event_type == "comment.created" and event.user_id:
            active_rules = db.query(Rule).filter(Rule.active.is_(True)).all()
            for rule in matching_rules(active_rules, event.text):
                if _create_job_or_record_duplicate(db, event, rule):
                    jobs_created += 1
                else:
                    duplicates_blocked += 1

        # comment.deleted and unknown event types are deliberately no-op work.
        event.processed = True
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info(
        "Event processed: event_id=%s jobs_created=%s duplicates_blocked=%s",
        event_id,
        jobs_created,
        duplicates_blocked,
    )
    return EventProcessingResult(True, False, jobs_created, duplicates_blocked)


def _create_job_or_record_duplicate(db: Session, event: Event, rule: Rule) -> bool:
    """Create a job, letting the database decide whether it is a duplicate."""
    try:
        with db.begin_nested():
            job = DMJob(
                rule_id=rule.id,
                event_id=event.event_id,
                comment_id=event.comment_id,
                recipient_user_id=event.user_id,
                message=rule.dm_message,
                status=DMJobStatus.QUEUED,
                attempts=0,
                dm_id=None,
                next_retry_at=None,
                last_error=None,
            )
            db.add(job)
            db.flush()
        return True
    except IntegrityError as exc:
        if not _is_duplicate_dm_job_error(exc):
            raise

        db.add(
            DMJobDuplicateBlock(
                rule_id=rule.id,
                event_id=event.event_id,
                recipient_user_id=event.user_id,
            ),
        )
        return False


def _is_duplicate_dm_job_error(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower() if exc.orig else str(exc).lower()
    is_unique_violation = "unique" in message or "duplicate" in message
    return is_unique_violation and "dm_jobs.rule_id" in message and "recipient_user_id" in message
