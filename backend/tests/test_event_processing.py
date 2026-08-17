import concurrent.futures
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import DMJob, DMJobDuplicateBlock, DMJobStatus, Event, Rule
from app.services import event_processor


def _create_rule(
    db: Session,
    keyword: str = "price",
    message: str = "Here is the price list.",
    *,
    active: bool = True,
) -> Rule:
    rule = Rule(keyword=keyword, dm_message=message, active=active)
    db.add(rule)
    db.commit()
    return rule


def _create_event(
    db: Session,
    event_id: str,
    *,
    event_type: str = "comment.created",
    user_id: str | None = "user-1",
    username: str | None = "first.username",
    text: str | None = "Can I get the PRICE?",
) -> Event:
    event = Event(
        event_id=event_id,
        event_type=event_type,
        comment_id=f"comment-{event_id}",
        user_id=user_id,
        username=username,
        text=text,
        payload={"event_id": event_id},
        processed=False,
    )
    db.add(event)
    db.commit()
    return event


def test_matching_comment_creates_queued_dm_job_with_correct_fields(
    db_session: Session,
) -> None:
    rule = _create_rule(db_session)
    event = _create_event(db_session, "evt-match")

    result = event_processor.process_event(db_session, event.event_id)

    job = db_session.query(DMJob).one()
    stored_event = db_session.get(Event, event.id)
    assert result.jobs_created == 1
    assert job.rule_id == rule.id
    assert job.event_id == event.event_id
    assert job.comment_id == event.comment_id
    assert job.recipient_user_id == "user-1"
    assert job.message == "Here is the price list."
    assert job.status == DMJobStatus.QUEUED
    assert job.attempts == 0
    assert job.dm_id is None
    assert job.next_retry_at is None
    assert job.last_error is None
    assert stored_event is not None and stored_event.processed is True


def test_process_pending_events_recovers_persisted_unprocessed_events(
    db_session: Session,
) -> None:
    _create_rule(db_session)
    event = _create_event(db_session, "evt-recovery")

    results = event_processor.process_pending_events(db_session)

    assert len(results) == 1
    assert results[0].jobs_created == 1
    assert db_session.get(Event, event.id).processed is True
    assert db_session.query(DMJob).count() == 1


@pytest.mark.parametrize(
    "text",
    ["PRICE", "price please", "Can I get the PRICE?", "PRICE???"],
)
def test_matching_is_case_insensitive_and_uses_substrings(
    db_session: Session,
    text: str,
) -> None:
    _create_rule(db_session)
    event = _create_event(db_session, f"evt-{text}", text=text)

    event_processor.process_event(db_session, event.event_id)

    assert db_session.query(DMJob).count() == 1


def test_non_matching_or_inactive_rules_create_no_jobs(db_session: Session) -> None:
    _create_rule(db_session, keyword="price")
    _create_rule(db_session, keyword="catalog", active=False)
    first = _create_event(db_session, "evt-no-match", text="Hello there")
    second = _create_event(db_session, "evt-inactive", text="catalog please", user_id="user-2")

    event_processor.process_event(db_session, first.event_id)
    event_processor.process_event(db_session, second.event_id)

    assert db_session.query(DMJob).count() == 0
    assert db_session.get(Event, first.id).processed is True
    assert db_session.get(Event, second.id).processed is True


def test_same_user_same_rule_is_blocked_by_database_constraint(
    db_session: Session,
) -> None:
    _create_rule(db_session)
    first = _create_event(db_session, "evt-first")
    second = _create_event(db_session, "evt-second", text="price please")

    event_processor.process_event(db_session, first.event_id)
    result = event_processor.process_event(db_session, second.event_id)

    assert db_session.query(DMJob).count() == 1
    assert result.duplicates_blocked == 1
    block = db_session.query(DMJobDuplicateBlock).one()
    assert block.event_id == second.event_id
    assert block.recipient_user_id == "user-1"
    assert db_session.get(Event, second.id).processed is True


def test_different_users_and_different_rules_can_each_receive_jobs(
    db_session: Session,
) -> None:
    first_rule = _create_rule(db_session, message="First price list")
    second_rule = _create_rule(db_session, message="Second price list")
    first = _create_event(db_session, "evt-user-one", user_id="user-1")
    second = _create_event(db_session, "evt-user-two", user_id="user-2")

    event_processor.process_event(db_session, first.event_id)
    event_processor.process_event(db_session, second.event_id)

    jobs = db_session.query(DMJob).all()
    assert len(jobs) == 4
    assert {(job.rule_id, job.recipient_user_id) for job in jobs} == {
        (first_rule.id, "user-1"),
        (first_rule.id, "user-2"),
        (second_rule.id, "user-1"),
        (second_rule.id, "user-2"),
    }


def test_one_comment_matching_two_rules_creates_two_jobs(db_session: Session) -> None:
    _create_rule(db_session, keyword="price")
    _create_rule(db_session, keyword="catalog")
    event = _create_event(db_session, "evt-two-rules", text="Send the price catalog")

    result = event_processor.process_event(db_session, event.event_id)

    assert result.jobs_created == 2
    assert db_session.query(DMJob).count() == 2


@pytest.mark.parametrize("event_type", ["comment.deleted", "post.created"])
def test_non_comment_created_events_create_no_jobs(
    db_session: Session,
    event_type: str,
) -> None:
    _create_rule(db_session)
    event = _create_event(db_session, f"evt-{event_type}", event_type=event_type)

    event_processor.process_event(db_session, event.event_id)

    assert db_session.query(DMJob).count() == 0
    assert db_session.get(Event, event.id).processed is True


def test_username_changes_do_not_change_recipient_identity(db_session: Session) -> None:
    _create_rule(db_session)
    first = _create_event(
        db_session,
        "evt-identity-one",
        user_id="stable-user-id",
        username="old.username",
    )
    second = _create_event(
        db_session,
        "evt-identity-two",
        user_id="stable-user-id",
        username="new.username",
    )

    event_processor.process_event(db_session, first.event_id)
    event_processor.process_event(db_session, second.event_id)

    assert db_session.query(DMJob).count() == 1
    assert db_session.query(DMJobDuplicateBlock).one().recipient_user_id == "stable-user-id"


def test_failed_job_creation_rolls_back_and_leaves_event_unprocessed(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_rule(db_session)
    event = _create_event(db_session, "evt-rollback")

    def fail_job_creation(*_args, **_kwargs) -> bool:
        raise SQLAlchemyError("database write failed")

    monkeypatch.setattr(event_processor, "_create_job_or_record_duplicate", fail_job_creation)

    with pytest.raises(SQLAlchemyError):
        event_processor.process_event(db_session, event.event_id)

    db_session.expire_all()
    assert db_session.query(DMJob).count() == 0
    assert db_session.get(Event, event.id).processed is False


def test_concurrent_processing_uses_real_unique_constraint(tmp_path: Path) -> None:
    database_path = tmp_path / "event-processing.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)

    setup_session = SessionLocal()
    try:
        _create_rule(setup_session)
        first = _create_event(setup_session, "evt-concurrent-one")
        second = _create_event(setup_session, "evt-concurrent-two")
        event_ids = [first.event_id, second.event_id]
    finally:
        setup_session.close()

    def process(event_id: str) -> None:
        session = SessionLocal()
        try:
            event_processor.process_event(session, event_id)
        finally:
            session.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(process, event_ids))

        verify_session = SessionLocal()
        try:
            assert verify_session.query(DMJob).count() == 1
            assert verify_session.query(DMJobDuplicateBlock).count() == 1
            assert verify_session.query(Event).filter(Event.processed.is_(True)).count() == 2
        finally:
            verify_session.close()
    finally:
        engine.dispose()
