import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.rule import Rule

VALID_PAYLOAD = {
    "keyword": "PRICE",
    "dm_message": "Here's the price list: ...",
}


def test_post_rules_creates_rule(client: TestClient, db_session: Session) -> None:
    response = client.post("/rules", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert "rule_id" in body
    assert body["keyword"] == "price"
    assert body["dm_message"] == VALID_PAYLOAD["dm_message"]

    stored = db_session.get(Rule, uuid.UUID(body["rule_id"]))
    assert stored is not None
    assert stored.keyword == "price"
    assert stored.dm_message == VALID_PAYLOAD["dm_message"]


def test_post_rules_response_shape(client: TestClient) -> None:
    response = client.post("/rules", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"rule_id", "keyword", "dm_message"}


def test_post_rules_normalizes_keyword(client: TestClient) -> None:
    response = client.post(
        "/rules",
        json={"keyword": "  PrIcE  ", "dm_message": "Hello"},
    )

    assert response.status_code == 201
    assert response.json()["keyword"] == "price"


def test_post_rules_preserves_dm_message(client: TestClient) -> None:
    message = "  Here's the price list: ...  "
    response = client.post(
        "/rules",
        json={"keyword": "PRICE", "dm_message": message},
    )

    assert response.status_code == 201
    assert response.json()["dm_message"] == message


@pytest.mark.parametrize(
    "payload",
    [
        {"dm_message": "Hello"},
        {"keyword": "", "dm_message": "Hello"},
        {"keyword": "   ", "dm_message": "Hello"},
    ],
)
def test_post_rules_rejects_invalid_keyword(
    client: TestClient,
    payload: dict,
) -> None:
    response = client.post("/rules", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"keyword": "PRICE"},
        {"keyword": "PRICE", "dm_message": ""},
        {"keyword": "PRICE", "dm_message": "   "},
    ],
)
def test_post_rules_rejects_invalid_dm_message(
    client: TestClient,
    payload: dict,
) -> None:
    response = client.post("/rules", json=payload)
    assert response.status_code == 422


def test_get_rules_returns_active_rules(client: TestClient) -> None:
    client.post("/rules", json={"keyword": "PRICE", "dm_message": "Msg 1"})
    client.post("/rules", json={"keyword": "INFO", "dm_message": "Msg 2"})

    response = client.get("/rules")

    assert response.status_code == 200
    rules = response.json()
    assert len(rules) == 2
    keywords = {rule["keyword"] for rule in rules}
    assert keywords == {"price", "info"}


def test_get_rule_by_id(client: TestClient) -> None:
    created = client.post("/rules", json=VALID_PAYLOAD).json()
    rule_id = created["rule_id"]

    response = client.get(f"/rules/{rule_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["rule_id"] == rule_id
    assert body["keyword"] == "price"
    assert body["dm_message"] == VALID_PAYLOAD["dm_message"]


def test_get_rule_by_invalid_id_returns_404(client: TestClient) -> None:
    response = client.get("/rules/not-a-valid-uuid")
    assert response.status_code == 404

    missing = client.get(f"/rules/{uuid.uuid4()}")
    assert missing.status_code == 404


def test_health_still_works(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "linkplease-automation",
    }
