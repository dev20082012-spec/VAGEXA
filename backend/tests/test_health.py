import pytest
from fastapi.testclient import TestClient


def test_live_does_not_require_a_body(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"
    assert response.headers["X-Request-ID"]


def test_ready_when_database_is_up(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_fails_when_database_check_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("vagexa.api.routers.health.check_database", broken)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not-ready"


def test_validation_error_is_problem_json(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["request_id"]
    assert body["errors"]
