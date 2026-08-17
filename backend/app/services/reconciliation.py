import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models.delivery import Delivery, DeliveryStatus
from app.models.dm_job import DMJob, DMJobStatus
from app.services.pseudogram_client import PseudoGramClient

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ReconcileResult:
    processed: int


class ReconciliationWorker:
    """Durable reconciliation worker for accepted DMJobs / Deliveries.

    Scans Delivery rows with status QUEUED and polls PseudoGram for the DM status.
    Updates Delivery and DMJob rows according to external status.
    """

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        settings: Settings | None = None,
        client: PseudoGramClient | None = None,
        now: Callable[[], datetime] = _utc_now,
        check_interval_seconds: int = 15,
        batch_size: int = 100,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings or get_settings()
        self._client = client or PseudoGramClient(self._settings)
        self._now = now
        self._check_interval = timedelta(seconds=check_interval_seconds)
        self._batch_size = batch_size

    def run_once(self) -> ReconcileResult:
        now = self._now()
        cutoff = now - self._check_interval
        processed = 0

        with self._session_factory() as db:
            # Select deliveries that are queued and not recently checked.
            candidates = (
                db.query(Delivery)
                .filter(Delivery.status == DeliveryStatus.QUEUED)
                .filter((Delivery.last_checked_at.is_(None)) | (Delivery.last_checked_at <= cutoff))
                .order_by(Delivery.created_at.asc())
                .limit(self._batch_size)
                .all()
            )

            for delivery in candidates:
                processed += 1
                dm_id = delivery.dm_id
                if not dm_id:
                    delivery.last_checked_at = now
                    db.commit()
                    continue

                try:
                    resp = self._client.get_dm(dm_id)
                except Exception as exc:  # network/transport errors
                    logger.warning("reconciliation GET /v1/dm/%s failed: %s", dm_id, type(exc).__name__)
                    delivery.last_checked_at = now
                    db.commit()
                    continue

                # non-200 responses: update last_checked_at and retry later
                if resp.status_code != 200:
                    delivery.last_checked_at = now
                    db.commit()
                    continue

                status = resp.payload.get("status")
                if status == "delivered":
                    # mark delivery and dm_job delivered
                    delivery.status = DeliveryStatus.DELIVERED
                    delivery.last_checked_at = now
                    dm_job = db.get(DMJob, delivery.dm_job_id)
                    if dm_job is not None:
                        dm_job.status = DMJobStatus.DELIVERED
                    db.commit()
                    continue

                if status == "queued":
                    delivery.last_checked_at = now
                    db.commit()
                    continue

                if status == "failed":
                    # Map external failure -> schedule resend of DMJob
                    delivery.status = DeliveryStatus.FAILED
                    delivery.last_checked_at = now

                    dm_job = db.get(DMJob, delivery.dm_job_id)
                    if dm_job is not None:
                        # Clear the dm_id so future send attempts will create a new outbound DM
                        dm_job.dm_id = None
                        dm_job.status = DMJobStatus.RETRYING
                        dm_job.claimed_at = None
                        # compute backoff based on attempts
                        attempts = dm_job.attempts if dm_job.attempts is not None else 0
                        backoff = self._settings.dm_worker_retry_base_seconds * (2 ** max(attempts - 1, 0))
                        dm_job.next_retry_at = now + timedelta(seconds=backoff)
                        dm_job.last_error = "external failed"
                    db.commit()
                    continue

                # Unknown or missing status - update last_checked and try later
                delivery.last_checked_at = now
                db.commit()

        return ReconcileResult(processed=processed)


def run_once() -> ReconcileResult:
    return ReconciliationWorker().run_once()


def start_worker(poll_interval_seconds: float = 5.0) -> None:
    while True:
        result = run_once()
        if result.processed == 0:
            time.sleep(poll_interval_seconds)
