import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx
from sqlalchemy import and_, or_, update
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models.dm_job import DMJob, DMJobStatus
from app.models.dm_rate_limit_lock import DMRateLimitLock
from app.models.dm_send_attempt import DMSendAttempt
from app.models.delivery import Delivery, DeliveryStatus
from app.services.event_processor import process_pending_events
from app.services.pseudogram_client import PseudoGramClient, PseudoGramSendResponse

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW = timedelta(seconds=60)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ClaimedDMJob:
    id: uuid.UUID
    recipient_user_id: str
    message: str
    comment_id: str | None


@dataclass(frozen=True)
class WorkerRunResult:
    claimed: bool
    sent: bool
    rate_limited: bool


class DMWorker:
    """Durable, one-job-at-a-time worker for outbound DM acceptance requests."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        settings: Settings | None = None,
        client: PseudoGramClient | None = None,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings or get_settings()
        self._client = client or PseudoGramClient(self._settings)
        self._now = now

    def run_worker_once(self) -> WorkerRunResult:
        """Recover events, then claim and handle at most one durable DM job."""
        with self._session_factory() as db:
            process_pending_events(db)

        job = self._claim_next_job()
        if job is None:
            return WorkerRunResult(claimed=False, sent=False, rate_limited=False)

        allowed, retry_at = self._reserve_send_slot(job.id)
        if not allowed:
            self._release_for_rate_limit(job.id, retry_at)
            return WorkerRunResult(claimed=True, sent=False, rate_limited=True)

        try:
            response = self._client.send_dm(
                recipient_user_id=job.recipient_user_id,
                message=job.message,
                comment_id=job.comment_id,
                idempotency_key=build_idempotency_key(job.id),
            )
        except httpx.HTTPError as exc:
            self._schedule_retry_or_fail(job.id, f"transport error: {type(exc).__name__}")
            return WorkerRunResult(claimed=True, sent=True, rate_limited=False)
        except RuntimeError as exc:
            self._mark_failed(job.id, str(exc))
            return WorkerRunResult(claimed=True, sent=True, rate_limited=False)

        self._handle_response(job.id, response)
        return WorkerRunResult(claimed=True, sent=True, rate_limited=False)

    def _claim_next_job(self) -> ClaimedDMJob | None:
        now = self._now()
        stale_before = now - timedelta(seconds=self._settings.dm_worker_sending_lease_seconds)
        claimable = _claimable_condition(now, stale_before)

        with self._session_factory() as db:
            candidate_id = (
                db.query(DMJob.id)
                .filter(claimable)
                .order_by(DMJob.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
                .scalar()
            )
            if candidate_id is None:
                return None

            claimed = db.execute(
                update(DMJob)
                .where(DMJob.id == candidate_id, claimable)
                .values(
                    status=DMJobStatus.SENDING,
                    claimed_at=now,
                    next_retry_at=None,
                ),
            )
            if claimed.rowcount != 1:
                db.rollback()
                return None
            db.commit()

            job = db.get(DMJob, candidate_id)
            assert job is not None
            return ClaimedDMJob(
                id=job.id,
                recipient_user_id=job.recipient_user_id,
                message=job.message,
                comment_id=job.comment_id,
            )

    def _reserve_send_slot(self, job_id: uuid.UUID) -> tuple[bool, datetime]:
        now = self._now()
        cutoff = now - RATE_LIMIT_WINDOW
        with self._session_factory() as db:
            lock = (
                db.query(DMRateLimitLock)
                .filter(DMRateLimitLock.id == 1)
                .with_for_update()
                .one_or_none()
            )
            if lock is None:
                db.add(DMRateLimitLock(id=1))
                db.flush()

            timestamps = [
                attempted_at
                for (attempted_at,) in db.query(DMSendAttempt.attempted_at)
                .filter(DMSendAttempt.attempted_at >= cutoff)
                .order_by(DMSendAttempt.attempted_at.asc())
                .all()
            ]
            if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
                db.commit()
                return False, timestamps[0] + RATE_LIMIT_WINDOW

            db.add(DMSendAttempt(dm_job_id=job_id, attempted_at=now))
            db.execute(
                update(DMJob)
                .where(DMJob.id == job_id, DMJob.status == DMJobStatus.SENDING)
                .values(attempts=DMJob.attempts + 1),
            )
            db.commit()
            return True, now

    def _release_for_rate_limit(self, job_id: uuid.UUID, retry_at: datetime) -> None:
        with self._session_factory() as db:
            db.execute(
                update(DMJob)
                .where(DMJob.id == job_id, DMJob.status == DMJobStatus.SENDING)
                .values(
                    status=DMJobStatus.RETRYING,
                    claimed_at=None,
                    next_retry_at=retry_at,
                ),
            )
            db.commit()

    def _handle_response(self, job_id: uuid.UUID, response: PseudoGramSendResponse) -> None:
        if response.status_code == 202:
            dm_id = response.payload.get("dm_id")
            if isinstance(dm_id, str) and dm_id:
                self._mark_accepted(job_id, dm_id)
                return
            self._schedule_retry_or_fail(job_id, "202 response missing dm_id")
            return

        if response.status_code == 429:
            retry_at = self._now() + timedelta(
                seconds=response.retry_after_seconds
                if response.retry_after_seconds is not None
                else self._backoff_seconds_for(job_id),
            )
            self._schedule_retry_or_fail(job_id, "rate limited", retry_at=retry_at)
            return

        if response.status_code == 400:
            self._mark_failed(job_id, _response_error(response, "invalid request"))
            return

        if response.status_code >= 500:
            self._schedule_retry_or_fail(job_id, _response_error(response, "server error"))
            return

        self._mark_failed(job_id, _response_error(response, f"HTTP {response.status_code}"))

    def _mark_accepted(self, job_id: uuid.UUID, dm_id: str) -> None:
        """Mark the DMJob accepted and create a Delivery record for reconciliation.

        If a Delivery already exists for this DMJob, update its dm_id and recipient.
        """
        with self._session_factory() as db:
            db.execute(
                update(DMJob)
                .where(DMJob.id == job_id, DMJob.status == DMJobStatus.SENDING)
                .values(
                    status=DMJobStatus.ACCEPTED,
                    dm_id=dm_id,
                    claimed_at=None,
                    next_retry_at=None,
                    last_error=None,
                ),
            )

            # Create or update Delivery row for reconciliation
            job = db.get(DMJob, job_id)
            if job is not None:
                delivery = (
                    db.query(Delivery)
                    .filter(Delivery.dm_job_id == job_id)
                    .one_or_none()
                )
                if delivery is None:
                    delivery = Delivery(
                        dm_job_id=job_id,
                        dm_id=dm_id,
                        recipient_user_id=job.recipient_user_id,
                        status=DeliveryStatus.QUEUED,
                    )
                    db.add(delivery)
                else:
                    delivery.dm_id = dm_id
                    delivery.recipient_user_id = job.recipient_user_id
                    delivery.status = DeliveryStatus.QUEUED
            db.commit()

    def _schedule_retry_or_fail(
        self,
        job_id: uuid.UUID,
        error: str,
        *,
        retry_at: datetime | None = None,
    ) -> None:
        with self._session_factory() as db:
            job = db.get(DMJob, job_id)
            if job is None or job.status != DMJobStatus.SENDING:
                return
            if job.attempts >= self._settings.dm_worker_max_attempts:
                job.status = DMJobStatus.FAILED
                job.claimed_at = None
                job.next_retry_at = None
                job.last_error = error
            else:
                job.status = DMJobStatus.RETRYING
                job.claimed_at = None
                job.next_retry_at = retry_at or (
                    self._now() + timedelta(seconds=self._backoff_seconds(job.attempts))
                )
                job.last_error = error
            db.commit()

    def _mark_failed(self, job_id: uuid.UUID, error: str) -> None:
        with self._session_factory() as db:
            db.execute(
                update(DMJob)
                .where(DMJob.id == job_id, DMJob.status == DMJobStatus.SENDING)
                .values(
                    status=DMJobStatus.FAILED,
                    claimed_at=None,
                    next_retry_at=None,
                    last_error=error,
                ),
            )
            db.commit()

    def _backoff_seconds_for(self, job_id: uuid.UUID) -> int:
        with self._session_factory() as db:
            job = db.get(DMJob, job_id)
            return self._backoff_seconds(job.attempts if job is not None else 1)

    def _backoff_seconds(self, attempts: int) -> int:
        return self._settings.dm_worker_retry_base_seconds * (2 ** max(attempts - 1, 0))


def build_idempotency_key(job_id: uuid.UUID) -> str:
    """Stable retry-safe idempotency key for one logical DM job."""
    return f"linkplease-dm-job-{job_id}"


def run_worker_once() -> WorkerRunResult:
    """Process durable work once; suitable for schedulers and integration tests."""
    return DMWorker().run_worker_once()


def start_worker(poll_interval_seconds: float = 1.0) -> None:
    """Continuously drain durable work in a dedicated worker process."""
    while True:
        result = run_worker_once()
        if not result.claimed or result.rate_limited:
            time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    start_worker()


def _claimable_condition(now: datetime, stale_before: datetime):
    return or_(
        DMJob.status == DMJobStatus.QUEUED,
        and_(
            DMJob.status == DMJobStatus.RETRYING,
            or_(DMJob.next_retry_at.is_(None), DMJob.next_retry_at <= now),
        ),
        and_(
            DMJob.status == DMJobStatus.SENDING,
            or_(DMJob.claimed_at.is_(None), DMJob.claimed_at <= stale_before),
        ),
    )


def _response_error(response: PseudoGramSendResponse, fallback: str) -> str:
    error = response.payload.get("error")
    detail = response.payload.get("detail")
    if isinstance(error, str) and isinstance(detail, str):
        return f"{error}: {detail}"
    if isinstance(error, str):
        return error
    return fallback
