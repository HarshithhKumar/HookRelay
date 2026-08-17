import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas.webhook import (
    ParsedWebhookEvent,
    WebhookAcceptedResponse,
    WebhookEventRequest,
)
from app.security.webhook import verify_webhook_signature
from app.services import webhook_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

SIGNATURE_HEADER = "X-PseudoGram-Signature"


@router.post(
    "/webhook",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_200_OK,
)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookAcceptedResponse:
    raw_body = await request.body()
    signature = request.headers.get(SIGNATURE_HEADER)

    _verify_signature_or_raise(settings, raw_body, signature)

    payload = _parse_json_or_raise(raw_body)
    parsed = _validate_event_or_raise(payload)

    _, is_new = webhook_service.persist_event(db, parsed)
    if is_new:
        background_tasks.add_task(
            webhook_service.schedule_event_processing,
            parsed.event_id,
        )
        logger.info(
            "Webhook accepted: event_id=%s event_type=%s",
            parsed.event_id,
            parsed.event_type,
        )
        return WebhookAcceptedResponse(status="accepted")

    return WebhookAcceptedResponse(status="duplicate")


def _verify_signature_or_raise(
    settings: Settings,
    raw_body: bytes,
    signature: str | None,
) -> None:
    api_key = settings.pseudogram_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    if not verify_webhook_signature(api_key, raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )


def _parse_json_or_raise(raw_body: bytes) -> dict:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    return payload


def _validate_event_or_raise(payload: dict) -> ParsedWebhookEvent:
    try:
        validated = WebhookEventRequest.model_validate(payload)
        return ParsedWebhookEvent.from_validated(validated, original_payload=payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc
