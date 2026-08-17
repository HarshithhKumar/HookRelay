import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

# Ensure backend/ is on the path when running pytest from any directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.models import (  # noqa: E402
    Delivery,
    DeliveryStatus,
    DMJob,
    DMJobStatus,
    Event,
    Rule,
)


@pytest.fixture()
def db_session() -> Session:
    """In-memory SQLite session with the full schema applied."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_rule_insert(db_session: Session) -> None:
    rule = Rule(keyword="hello", dm_message="Thanks for commenting!")
    db_session.add(rule)
    db_session.commit()

    stored = db_session.query(Rule).one()
    assert stored.keyword == "hello"
    assert stored.dm_message == "Thanks for commenting!"
    assert stored.active is True


def test_event_insert(db_session: Session) -> None:
    event = Event(
        event_id="evt-001",
        event_type="comment.created",
        comment_id="cmt-001",
        payload={"raw": True},
    )
    db_session.add(event)
    db_session.commit()

    stored = db_session.query(Event).one()
    assert stored.event_id == "evt-001"
    assert stored.processed is False


def test_duplicate_event_id_rejected(db_session: Session) -> None:
    db_session.add(
        Event(event_id="evt-dup", event_type="comment.created"),
    )
    db_session.commit()

    db_session.add(
        Event(event_id="evt-dup", event_type="comment.created"),
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_dm_job_rule_recipient_rejected(db_session: Session) -> None:
    rule = Rule(keyword="sale", dm_message="Here is your link!")
    db_session.add(rule)
    db_session.flush()

    db_session.add(
        Event(event_id="evt-a", event_type="comment.created"),
    )
    db_session.add(
        Event(event_id="evt-b", event_type="comment.created"),
    )
    db_session.flush()

    db_session.add(
        DMJob(
            rule_id=rule.id,
            event_id="evt-a",
            recipient_user_id="user-42",
            message="Here is your link!",
            status=DMJobStatus.QUEUED,
        ),
    )
    db_session.commit()

    db_session.add(
        DMJob(
            rule_id=rule.id,
            event_id="evt-b",
            recipient_user_id="user-42",
            message="Here is your link!",
            status=DMJobStatus.QUEUED,
        ),
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_delivery_references_dm_job(db_session: Session) -> None:
    rule = Rule(keyword="info", dm_message="Details inside.")
    db_session.add(rule)
    db_session.flush()

    db_session.add(
        Event(event_id="evt-delivery", event_type="comment.created"),
    )
    db_session.flush()

    dm_job = DMJob(
        rule_id=rule.id,
        event_id="evt-delivery",
        recipient_user_id="user-99",
        message="Details inside.",
        status=DMJobStatus.ACCEPTED,
        dm_id="dm-123",
    )
    db_session.add(dm_job)
    db_session.flush()

    delivery = Delivery(
        dm_job_id=dm_job.id,
        dm_id="dm-123",
        status=DeliveryStatus.QUEUED,
        recipient_user_id="user-99",
    )
    db_session.add(delivery)
    db_session.commit()

    stored = db_session.query(Delivery).one()
    assert stored.dm_job_id == dm_job.id
    assert stored.dm_id == "dm-123"
    assert stored.status == DeliveryStatus.QUEUED


def test_application_starts() -> None:
    """Importing the FastAPI app must succeed without a running database."""
    from app.main import app  # noqa: F401

    assert app.title == "LinkPlease Automation API"
