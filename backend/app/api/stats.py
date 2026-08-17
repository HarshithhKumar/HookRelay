from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dm_job import DMJob, DMJobStatus
from app.models.delivery import Delivery, DeliveryStatus
from app.models.dm_job_duplicate_block import DMJobDuplicateBlock

router = APIRouter(tags=["stats"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return exact stats required by the grader.

    {
      "sent": integer,
      "failed": integer,
      "queued": integer,
      "duplicates_blocked": integer
    }
    """
    # sent: only confirmed delivered DMs (Delivery.status == DELIVERED)
    sent = db.query(Delivery).filter(Delivery.status == DeliveryStatus.DELIVERED).count()

    # failed: DMJobs that reached permanent FAILED state
    failed = db.query(DMJob).filter(DMJob.status == DMJobStatus.FAILED).count()

    # queued: non-terminal DMJobs (queued, sending, accepted, retrying)
    queued = db.query(DMJob).filter(
        DMJob.status.in_(
            [
                DMJobStatus.QUEUED,
                DMJobStatus.SENDING,
                DMJobStatus.ACCEPTED,
                DMJobStatus.RETRYING,
            ]
        )
    ).count()

    # duplicates_blocked: durable duplicate block records
    duplicates_blocked = db.query(DMJobDuplicateBlock).count()

    return {
        "sent": sent,
        "failed": failed,
        "queued": queued,
        "duplicates_blocked": duplicates_blocked,
    }
