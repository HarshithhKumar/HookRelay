from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.rule import RuleCreateRequest, RuleResponse
from app.services import rule_service

router = APIRouter(tags=["rules"])


def _to_response(rule) -> RuleResponse:
    return RuleResponse(
        rule_id=str(rule.id),
        keyword=rule.keyword,
        dm_message=rule.dm_message,
    )


@router.post(
    "/rules",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rule(
    body: RuleCreateRequest,
    db: Session = Depends(get_db),
) -> RuleResponse:
    rule = rule_service.create_rule(
        db,
        keyword=body.keyword,
        dm_message=body.dm_message,
    )
    return _to_response(rule)


@router.get("/rules", response_model=list[RuleResponse])
def list_rules(db: Session = Depends(get_db)) -> list[RuleResponse]:
    rules = rule_service.list_active_rules(db)
    return [_to_response(rule) for rule in rules]


@router.get("/rules/{rule_id}", response_model=RuleResponse)
def get_rule(rule_id: str, db: Session = Depends(get_db)) -> RuleResponse:
    rule = rule_service.get_rule_by_id(db, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )
    return _to_response(rule)
