from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings


@dataclass(frozen=True)
class PseudoGramSendResponse:
    status_code: int
    payload: dict[str, Any]
    retry_after_seconds: int | None


@dataclass(frozen=True)
class PseudoGramGetResponse:
    status_code: int
    payload: dict[str, Any]


class PseudoGramClient:
    """Small HTTP boundary for the PseudoGram DM-send API and DM status API."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = settings.pseudogram_api_key
        self._base_url = settings.pseudogram_base_url.rstrip("/")
        self._timeout = httpx.Timeout(10.0, connect=5.0)
        self._transport = transport

    def send_dm(
        self,
        *,
        recipient_user_id: str,
        message: str,
        comment_id: str | None,
        idempotency_key: str,
    ) -> PseudoGramSendResponse:
        if not self._api_key:
            raise RuntimeError("PseudoGram API key is not configured")

        with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
            response = client.post(
                f"{self._base_url}/v1/dm/send",
                headers={
                    "X-API-Key": self._api_key,
                    "Idempotency-Key": idempotency_key,
                },
                json={
                    "recipient_user_id": recipient_user_id,
                    "message": message,
                    "comment_id": comment_id,
                },
            )

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        return PseudoGramSendResponse(
            status_code=response.status_code,
            payload=payload if isinstance(payload, dict) else {},
            retry_after_seconds=retry_after,
        )

    def get_dm(self, dm_id: str) -> PseudoGramGetResponse:
        """Fetch DM status from PseudoGram by dm_id.

        Returns a small wrapper with status_code and parsed JSON payload.
        """
        if not self._api_key:
            raise RuntimeError("PseudoGram API key is not configured")

        with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
            response = client.get(
                f"{self._base_url}/v1/dm/{dm_id}",
                headers={"X-API-Key": self._api_key},
            )
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        return PseudoGramGetResponse(status_code=response.status_code, payload=payload if isinstance(payload, dict) else {})


def _parse_retry_after(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        seconds = int(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
