from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookFromUser(BaseModel):
    user_id: str | None = None
    username: str | None = None


class WebhookData(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    comment_id: str | None = None
    post_id: str | None = None
    text: str | None = None
    from_user: WebhookFromUser | None = Field(default=None, alias="from")


class WebhookEventRequest(BaseModel):
    event_id: str
    event_type: str
    sent_at: datetime
    data: dict[str, Any]

    @field_validator("event_id", "event_type")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()


class WebhookAcceptedResponse(BaseModel):
    status: Literal["accepted", "duplicate"]


class ParsedWebhookEvent(BaseModel):
    event_id: str
    event_type: str
    sent_at: datetime
    comment_id: str | None = None
    post_id: str | None = None
    user_id: str | None = None
    username: str | None = None
    text: str | None = None
    payload: dict[str, Any]

    @classmethod
    def from_validated(
        cls,
        event: WebhookEventRequest,
        *,
        original_payload: dict[str, Any],
    ) -> "ParsedWebhookEvent":
        validated_data = WebhookData.model_validate(event.data)
        from_user = validated_data.from_user

        return cls(
            event_id=event.event_id,
            event_type=event.event_type,
            sent_at=event.sent_at,
            comment_id=validated_data.comment_id,
            post_id=validated_data.post_id,
            user_id=from_user.user_id if from_user else None,
            username=from_user.username if from_user else None,
            text=validated_data.text,
            payload=original_payload,
        )
