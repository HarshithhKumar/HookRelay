import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.rule import Rule


def normalize_keyword(keyword: str) -> str:
    """Trim and lowercase a keyword for consistent case-insensitive matching."""
    return keyword.strip().lower()


def create_rule(db: Session, keyword: str, dm_message: str) -> Rule:
    rule = Rule(keyword=keyword, dm_message=dm_message)
    db.add(rule)
    try:
        db.commit()
        db.refresh(rule)
    except SQLAlchemyError:
        db.rollback()
        raise
    return rule


def list_active_rules(db: Session) -> list[Rule]:
    return (
        db.query(Rule)
        .filter(Rule.active.is_(True))
        .order_by(Rule.created_at.desc())
        .all()
    )


def get_rule_by_id(db: Session, rule_id: str) -> Rule | None:
    try:
        parsed_id = uuid.UUID(rule_id)
    except ValueError:
        return None

    return db.query(Rule).filter(Rule.id == parsed_id).one_or_none()
