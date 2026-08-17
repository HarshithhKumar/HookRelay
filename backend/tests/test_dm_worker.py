import concurrent.futures
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import DMJob, DMJobStatus, Event, Rule
from app.services.dm_worker import DMWorker, RATE_LIMIT_WINDOW, build_idempotency_key
from app.services.pseudogram_client import PseudoGramClient, PseudoGramSendResponse


class RecordingClient:
    def __init__(self, outcomes: list[PseudoGramSendResponse | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict] = []

    def send_dm(self, **kwargs) -> PseudoGramSendResponse:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def accepted(dm_id: str = "dm-accepted") -> PseudoGramSendResponse:
    return PseudoGramSendResponse(202, {"dm_id": dm_id, "status": "queued"}, None)


def response(
    status_code: int,
    payload: dict | None = None,
    retry_after: int | None = None,
) -> PseudoGramSendResponse:
    return PseudoGramSendResponse(status_code, payload or {}, retry_after)


def make_settings(**overrides):
    values = {
        "pseudogram_api_key": "worker-test-key",
        "pseudogram_base_url": "https://example.invalid",
        "dm_worker_max_attempts": 3,
        "dm_worker_retry_base_seconds": 30,
        "dm_worker_sending_lease_seconds": 120,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def create_job(
    db: Session,
    *,
    user_id: str = "user-1",
    status: DMJobStatus = DMJobStatus.QUEUED,
    next_retry_at: datetime | None = None,
    claimed_at: datetime | None = None,
) -> DMJob:
    rule = Rule(keyword=f"price-{uuid.uuid4()}", dm_message="Price list")
    event = Event(
        event_id=f"evt-{uuid.uuid4()}",
        event_type="comment.created",
        comment_id="comment-1",
        user_id=user_id,
        text="price",
        payload={},
        processed=True,
    )
    db.add_all([rule, event])
    db.flush()
    job = DMJob(
        rule_id=rule.id,
        event_id=event.event_id,
        comment_id=event.comment_id,
        recipient_user_id=user_id,
        message=rule.dm_message,
        status=status,
        next_retry_at=next_retry_at,
        claimed_at=claimed_at,
    )
    db.add(job)
    db.commit()
    return job


def make_worker(
    db_engine,
    client: RecordingClient,
    now_holder: list[datetime],
    **settings_overrides,
) -> DMWorker:
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False)
    return DMWorker(
        session_factory=SessionLocal,
        settings=make_settings(**settings_overrides),
        client=client,
        now=lambda: now_holder[0],
    )


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def test_queued_job_sends_expected_payload_headers_and_becomes_accepted(
    db_session: Session,
    db_engine,
) -> None:
    job = create_job(db_session)
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    client = RecordingClient([accepted("dm-123")])
    worker = make_worker(db_engine, client, now)

    result = worker.run_worker_once()

    db_session.expire_all()
    stored = db_session.get(DMJob, job.id)
    assert result.claimed is True and result.sent is True
    assert client.calls == [
        {
            "recipient_user_id": "user-1",
            "message": "Price list",
            "comment_id": "comment-1",
            "idempotency_key": build_idempotency_key(job.id),
        },
    ]
    assert stored.status == DMJobStatus.ACCEPTED
    assert stored.dm_id == "dm-123"
    assert stored.status != DMJobStatus.DELIVERED


def test_pseudogram_client_sends_required_api_and_idempotency_headers() -> None:
    observed: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["headers"] = request.headers
        observed["json"] = json.loads(request.content)
        return httpx.Response(202, json={"dm_id": "dm-client", "status": "queued"})

    client = PseudoGramClient(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )
    result = client.send_dm(
        recipient_user_id="recipient-1",
        message="A message",
        comment_id="comment-1",
        idempotency_key="stable-key",
    )

    assert observed["url"] == "https://example.invalid/v1/dm/send"
    assert observed["headers"]["X-API-Key"] == "worker-test-key"
    assert observed["headers"]["Idempotency-Key"] == "stable-key"
    assert observed["json"] == {
        "recipient_user_id": "recipient-1",
        "message": "A message",
        "comment_id": "comment-1",
    }
    assert result.payload["dm_id"] == "dm-client"


def test_idempotency_key_is_stable_across_retry(
    db_session: Session,
    db_engine,
) -> None:
    job = create_job(db_session)
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    client = RecordingClient([response(500), accepted("dm-after-retry")])
    worker = make_worker(db_engine, client, now)

    worker.run_worker_once()
    now[0] += timedelta(seconds=30)
    worker.run_worker_once()

    assert [call["idempotency_key"] for call in client.calls] == [
        build_idempotency_key(job.id),
        build_idempotency_key(job.id),
    ]


def test_http_500_retries_then_fails_after_configured_max_attempts(
    db_session: Session,
    db_engine,
) -> None:
    job = create_job(db_session)
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    client = RecordingClient([response(500), response(500)])
    worker = make_worker(db_engine, client, now, dm_worker_max_attempts=2)

    worker.run_worker_once()
    db_session.expire_all()
    retrying = db_session.get(DMJob, job.id)
    assert retrying.status == DMJobStatus.RETRYING
    assert retrying.attempts == 1
    assert as_utc(retrying.next_retry_at) == now[0] + timedelta(seconds=30)

    now[0] += timedelta(seconds=30)
    worker.run_worker_once()
    db_session.expire_all()
    failed = db_session.get(DMJob, job.id)
    assert failed.status == DMJobStatus.FAILED
    assert failed.attempts == 2
    assert failed.last_error == "server error"


def test_http_429_uses_retry_after_and_keeps_job_retryable(
    db_session: Session,
    db_engine,
) -> None:
    job = create_job(db_session)
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    worker = make_worker(db_engine, RecordingClient([response(429, retry_after=17)]), now)

    worker.run_worker_once()

    db_session.expire_all()
    stored = db_session.get(DMJob, job.id)
    assert stored.status == DMJobStatus.RETRYING
    assert as_utc(stored.next_retry_at) == now[0] + timedelta(seconds=17)
    assert stored.last_error == "rate limited"


def test_http_400_is_immediately_failed_without_retry(
    db_session: Session,
    db_engine,
) -> None:
    job = create_job(db_session)
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    worker = make_worker(
        db_engine,
        RecordingClient([response(400, {"error": "invalid_request", "detail": "bad comment"})]),
        now,
    )

    worker.run_worker_once()

    db_session.expire_all()
    stored = db_session.get(DMJob, job.id)
    assert stored.status == DMJobStatus.FAILED
    assert stored.attempts == 1
    assert stored.next_retry_at is None
    assert stored.last_error == "invalid_request: bad comment"


def test_network_timeout_is_retryable(
    db_session: Session,
    db_engine,
) -> None:
    job = create_job(db_session)
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    worker = make_worker(db_engine, RecordingClient([httpx.ReadTimeout("timed out")]), now)

    worker.run_worker_once()

    db_session.expire_all()
    stored = db_session.get(DMJob, job.id)
    assert stored.status == DMJobStatus.RETRYING
    assert stored.last_error == "transport error: ReadTimeout"


def test_rate_limiter_allows_only_ten_of_twenty_jobs_in_a_rolling_window(
    db_session: Session,
    db_engine,
) -> None:
    jobs = [create_job(db_session, user_id=f"user-{index}") for index in range(20)]
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    client = RecordingClient([accepted(f"dm-{index}") for index in range(10)])
    worker = make_worker(db_engine, client, now)

    results = [worker.run_worker_once() for _ in jobs]

    db_session.expire_all()
    assert len(client.calls) == 10
    assert sum(result.rate_limited for result in results) == 10
    assert db_session.query(DMJob).filter(DMJob.status == DMJobStatus.ACCEPTED).count() == 10
    waiting = db_session.query(DMJob).filter(DMJob.status == DMJobStatus.RETRYING).all()
    assert len(waiting) == 10
    assert all(
        as_utc(job.next_retry_at) == now[0] + RATE_LIMIT_WINDOW
        for job in waiting
    )


def test_five_hundred_queued_jobs_remain_durable_after_first_rate_window(
    db_session: Session,
    db_engine,
) -> None:
    jobs = [create_job(db_session, user_id=f"load-user-{index}") for index in range(500)]
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    client = RecordingClient([accepted(f"dm-load-{index}") for index in range(10)])
    worker = make_worker(db_engine, client, now)

    for _ in jobs:
        worker.run_worker_once()

    db_session.expire_all()
    assert len(client.calls) == 10
    assert db_session.query(DMJob).filter(DMJob.status == DMJobStatus.ACCEPTED).count() == 10
    assert db_session.query(DMJob).filter(DMJob.status == DMJobStatus.RETRYING).count() == 490


def test_restart_recovers_retryable_and_stale_sending_jobs(
    db_session: Session,
    db_engine,
) -> None:
    now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
    retryable = create_job(
        db_session,
        user_id="retry-user",
        status=DMJobStatus.RETRYING,
        next_retry_at=now[0],
    )
    stale = create_job(
        db_session,
        user_id="stale-user",
        status=DMJobStatus.SENDING,
        claimed_at=now[0] - timedelta(seconds=121),
    )
    queued = create_job(db_session, user_id="queued-user")
    worker = make_worker(
        db_engine,
        RecordingClient([accepted("dm-r"), accepted("dm-s"), accepted("dm-q")]),
        now,
    )

    worker.run_worker_once()
    worker.run_worker_once()
    worker.run_worker_once()

    db_session.expire_all()
    assert db_session.get(DMJob, retryable.id).status == DMJobStatus.ACCEPTED
    assert db_session.get(DMJob, stale.id).status == DMJobStatus.ACCEPTED
    assert db_session.get(DMJob, queued.id).status == DMJobStatus.ACCEPTED


def test_two_workers_do_not_claim_the_same_job(tmp_path: Path) -> None:
    database_path = tmp_path / "worker-concurrency.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    setup = SessionLocal()
    try:
        job = create_job(setup)
        now = [datetime(2026, 8, 17, tzinfo=timezone.utc)]
        first_client = RecordingClient([accepted("dm-one")])
        second_client = RecordingClient([accepted("dm-two")])
        first_worker = DMWorker(
            session_factory=SessionLocal,
            settings=make_settings(),
            client=first_client,
            now=lambda: now[0],
        )
        second_worker = DMWorker(
            session_factory=SessionLocal,
            settings=make_settings(),
            client=second_client,
            now=lambda: now[0],
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda worker: worker.run_worker_once(), [first_worker, second_worker]))

        verify = SessionLocal()
        try:
            assert len(first_client.calls) + len(second_client.calls) == 1
            assert verify.get(DMJob, job.id).status == DMJobStatus.ACCEPTED
        finally:
            verify.close()
    finally:
        setup.close()
        engine.dispose()
