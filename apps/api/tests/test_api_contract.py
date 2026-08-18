"""The response envelope, error codes and request correlation."""

from __future__ import annotations

from tests.conftest import ALICE, auth


def test_health_returns_success_envelope(client) -> None:
    response = client.get("/api/v1/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["body"]["status"] == "ok"
    assert payload["request_id"].startswith("req_")
    assert response.headers["X-Request-ID"] == payload["request_id"]


def test_health_does_not_leak_credentials(client) -> None:
    body = client.get("/api/v1/health").json()["body"]
    serialized = str(body)
    assert "api_key" not in serialized
    assert "endpoint" not in serialized


def test_client_request_id_is_propagated(client) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "req_from_frontend"})
    assert response.json()["request_id"] == "req_from_frontend"


def test_missing_authentication_returns_401_envelope(client) -> None:
    response = client.get("/api/v1/accounts")
    payload = response.json()

    assert response.status_code == 401
    assert payload["success"] is False
    assert payload["error"]["code"] == "AUTH_REQUIRED"


def test_unknown_token_format_is_rejected(client) -> None:
    response = client.get("/api/v1/accounts", headers={"Authorization": "Bearer not-a-dev-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID"


def test_validation_error_uses_stable_code(client) -> None:
    response = client.post(
        "/api/v1/assistant/messages", json={"message": ""}, headers=auth(ALICE)
    )
    payload = response.json()

    assert response.status_code == 422
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in payload["error"]["details"]["fields"]


def test_unknown_route_returns_error_envelope(client) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
