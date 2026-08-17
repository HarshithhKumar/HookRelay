from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models.rule import Rule
from app.models.event import Event
from app.models.dm_job import DMJob, DMJobStatus
from app.models.delivery import Delivery, DeliveryStatus
from app.models.dm_send_attempt import DMSendAttempt
from app.config import get_settings

router = APIRouter(tags=["stats"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # Rules
    rules_count = db.query(Rule).count()

    # Events
    total_events = db.query(Event).count()
    processed_events = db.query(Event).filter(Event.processed == True).count()
    pending_events = total_events - processed_events

    # DM jobs by status
    jobs = {}
    for status in DMJobStatus:
        jobs[status.value] = db.query(DMJob).filter(DMJob.status == status).count()

    # Deliveries by status
    deliveries = {}
    for status in DeliveryStatus:
        deliveries[status.value] = db.query(Delivery).filter(Delivery.status == status).count()

    # Recent DM send attempts (rate limiter window)
    now = _utc_now()
    attempts_last_60s = db.query(DMSendAttempt).filter(DMSendAttempt.attempted_at >= (now - timedelta(seconds=60))).count()

    return {
        "rules": {"count": rules_count},
        "events": {
            "total": total_events,
            "processed": processed_events,
            "pending": pending_events,
        },
        "dm_jobs": jobs,
        "deliveries": deliveries,
        "rate_limiter": {"attempts_last_60s": attempts_last_60s},
    }
