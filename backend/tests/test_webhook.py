import concurrent.futures
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.event import Event
from app.security.webhook import SIGNATURE_PREFIX, compute_signature
from tests.conftest import TEST_API_KEY

SIGNATURE_HEADER = "X-PseudoGram-Signature"

COMMENT_CREATED_EVENT = {
    "event_id": "evt_01J8ZQ4K2N7RXA",
    "event_type": "comment.created",
    "sent_at": "2026-08-10T09:14:22.481Z",
    "data": {
        "comment_id": "cmt_9f2a7c",
        "post_id": "post_44de1b",
        "text": "PRICE please 🙏",
        "created_at": "2026-08-10T09:14:21.900Z",
        "from": {
            "user_id": "usr_3b91fe",
            "username": "arjun.shoots",
        },
    },
}

COMMENT_DELETED_EVENT = {
    "event_id": "evt_deleted_001",
    "event_type": "comment.deleted",
    "sent_at": "2026-08-10T09:14:22.481Z",
    "data": {
        "comment_id": "cmt_deleted_only",
    },
}


def sign_body(body: bytes, secret: str = TEST_API_KEY) -> dict[str, str]:
    signature = f"{SIGNATURE_PREFIX}{compute_signature(secret, body)}"
    return {SIGNATURE_HEADER: signature}


def post_signed_webhook(
    client: TestClient,
    payload: dict,
    *,
    secret: str = TEST_API_KEY,
    extra_headers: dict[str, str] | None = None,
) -> tuple[bytes, object]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = sign_body(body, secret=secret)
    if extra_headers:
        headers.update(extra_headers)
    response = client.post("/webhook", content=body, headers=headers)
    return body, response


def test_valid_signed_comment_created_returns_200(client: TestClient) -> None:
    _, response = post_signed_webhook(client, COMMENT_CREATED_EVENT)

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_valid_event_is_persisted(client: TestClient, db_session: Session) -> None:
    post_signed_webhook(client, COMMENT_CREATED_EVENT)

    stored = db_session.query(Event).filter_by(
        event_id=COMMENT_CREATED_EVENT["event_id"],
    ).one()

    assert stored.event_type == "comment.created"
    assert stored.comment_id == "cmt_9f2a7c"
    assert stored.post_id == "post_44de1b"
    assert stored.user_id == "usr_3b91fe"
    assert stored.username == "arjun.shoots"
    assert stored.text == "PRICE please 🙏"
    assert stored.payload == COMMENT_CREATED_EVENT
    assert stored.processed is False
    assert stored.received_at is not None
    assert stored.sent_at is not None


def test_missing_signature_returns_401(client: TestClient) -> None:
    body = json.dumps(COMMENT_CREATED_EVENT).encode("utf-8")
    response = client.post("/webhook", content=body)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid signature"


def test_invalid_signature_returns_401(client: TestClient) -> None:
    body = json.dumps(COMMENT_CREATED_EVENT).encode("utf-8")
    headers = {SIGNATURE_HEADER: "sha256=deadbeef"}
    response = client.post("/webhook", content=body, headers=headers)

    assert response.status_code == 401


def test_forged_event_is_not_persisted(client: TestClient, db_session: Session) -> None:
    body = json.dumps(COMMENT_CREATED_EVENT).encode("utf-8")
    response = client.post(
        "/webhook",
        content=body,
        headers={SIGNATURE_HEADER: "sha256=" + "0" * 64},
    )

    assert response.status_code == 401
    assert db_session.query(Event).count() == 0


def test_signature_uses_raw_request_bytes(client: TestClient) -> None:
    # Deliberate formatting must be preserved for signature verification.
    raw_body = (
        b'{"event_id":"evt_raw_bytes","event_type":"comment.created",'
        b'"sent_at":"2026-08-10T09:14:22.481Z","data":{"comment_id":"cmt_raw"}}'
    )
    response = client.post("/webhook", content=raw_body, headers=sign_body(raw_body))

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_reserialized_json_with_different_bytes_fails_signature(
    client: TestClient,
) -> None:
    payload = {
        "event_id": "evt_reserialize",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22.481Z",
        "data": {"comment_id": "cmt_1"},
    }
    signed_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    different_body = json.dumps(payload).encode("utf-8")
    headers = sign_body(signed_body)

    response = client.post("/webhook", content=different_body, headers=headers)
    assert response.status_code == 401


def test_invalid_json_returns_400(client: TestClient) -> None:
    raw_body = b"{not valid json"
    response = client.post("/webhook", content=raw_body, headers=sign_body(raw_body))

    assert response.status_code == 400


def test_malformed_nested_event_data_returns_422(client: TestClient) -> None:
    payload = {
        "event_id": "evt_bad_nested_data",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22.481Z",
        "data": {"from": "not-an-object"},
    }

    _, response = post_signed_webhook(client, payload)

    assert response.status_code == 422


def test_duplicate_event_returns_200_and_single_row(
    client: TestClient,
    db_session: Session,
) -> None:
    _, first = post_signed_webhook(client, COMMENT_CREATED_EVENT)
    _, second = post_signed_webhook(client, COMMENT_CREATED_EVENT)

    assert first.status_code == 200
    assert first.json()["status"] == "accepted"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert db_session.query(Event).count() == 1


def test_concurrent_duplicate_event_creates_one_row(
    client: TestClient,
    db_session: Session,
) -> None:
    payload = {
        "event_id": "evt_concurrent_dup",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22.481Z",
        "data": {"comment_id": "cmt_concurrent"},
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = sign_body(body)

    def send_webhook() -> int:
        response = client.post("/webhook", content=body, headers=headers)
        return response.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: send_webhook(), range(2)))

    assert all(status == 200 for status in statuses)
    assert db_session.query(Event).count() == 1


def test_comment_deleted_event_is_persisted(client: TestClient, db_session: Session) -> None:
    post_signed_webhook(client, COMMENT_DELETED_EVENT)

    stored = db_session.query(Event).filter_by(
        event_id=COMMENT_DELETED_EVENT["event_id"],
    ).one()

    assert stored.event_type == "comment.deleted"
    assert stored.comment_id == "cmt_deleted_only"
    assert stored.post_id is None
    assert stored.user_id is None
    assert stored.username is None
    assert stored.text is None


def test_user_id_is_identity_not_username(client: TestClient, db_session: Session) -> None:
    payload = {
        **COMMENT_CREATED_EVENT,
        "event_id": "evt_identity_check",
        "data": {
            **COMMENT_CREATED_EVENT["data"],
            "from": {
                "user_id": "usr_stable_id",
                "username": "changed.username",
            },
        },
    }
    post_signed_webhook(client, payload)

    stored = db_session.query(Event).one()
    assert stored.user_id == "usr_stable_id"
    assert stored.username == "changed.username"


def test_malformed_signature_prefix_returns_401(client: TestClient) -> None:
    body = json.dumps(COMMENT_CREATED_EVENT).encode("utf-8")
    headers = {SIGNATURE_HEADER: "md5=abc123"}
    response = client.post("/webhook", content=body, headers=headers)

    assert response.status_code == 401


def test_missing_api_key_rejects_webhook(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import get_settings

    monkeypatch.delenv("PSEUDOGRAM_API_KEY", raising=False)
    get_settings.cache_clear()

    body = json.dumps(COMMENT_CREATED_EVENT).encode("utf-8")
    headers = sign_body(body, secret=TEST_API_KEY)
    response = client.post("/webhook", content=body, headers=headers)

    assert response.status_code == 401

    get_settings.cache_clear()


def test_existing_rules_endpoints_still_work(client: TestClient) -> None:
    create_response = client.post(
        "/rules",
        json={"keyword": "PRICE", "dm_message": "Hello"},
    )
    assert create_response.status_code == 201
    rule_id = create_response.json()["rule_id"]

    list_response = client.get("/rules")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/rules/{rule_id}")
    assert get_response.status_code == 200

    health_response = client.get("/health")
    assert health_response.status_code == 200
