from fastapi.testclient import TestClient

from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings


def _user(username: str, password: str, role: str) -> None:
    init_engine(load_settings())
    db = open_session()
    try:
        create_user(db, username=username, display_name=username, password=password, role_names=[role])
        db.commit()
    finally:
        db.close()


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]


def test_investigator_creates_and_retrieves_a_case(client: TestClient) -> None:
    _user("investigator", "correct-horse", "investigator")
    _login(client, "investigator", "correct-horse")
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-A",
            "title": "Synthetic chain",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["reference"] == "SYN-A"
    assert body["data_classification"] == "synthetic"
    fetched = client.get(f"/api/v1/cases/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Synthetic chain"
    listed = client.get("/api/v1/cases")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == body["id"]


def test_unassigned_administrator_cannot_read_the_case(client: TestClient) -> None:
    _user("lead", "correct-horse", "investigator")
    _user("admin", "correct-horse", "administrator")
    _login(client, "lead", "correct-horse")
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-B",
            "title": "Hidden title",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    case_id = created.json()["id"]
    client.post("/api/v1/auth/logout")
    _login(client, "admin", "correct-horse")
    denied = client.get(f"/api/v1/cases/{case_id}")
    assert denied.status_code == 404
    assert "Hidden title" not in denied.text


def test_official_case_is_rejected_in_synthetic_mode(client: TestClient) -> None:
    _user("investigator2", "correct-horse", "investigator")
    _login(client, "investigator2", "correct-horse")
    response = client.post(
        "/api/v1/cases",
        json={
            "reference": "OFF-1",
            "title": "Should fail",
            "opened_on": "2026-01-15",
            "data_classification": "official",
        },
    )
    assert response.status_code == 422


def test_bad_password_matches_unknown_user(client: TestClient) -> None:
    _user("known", "correct-horse", "investigator")
    bad = client.post("/api/v1/auth/login", json={"username": "known", "password": "wrong-password"})
    missing = client.post("/api/v1/auth/login", json={"username": "missing", "password": "wrong-password"})
    assert bad.status_code == 401
    assert missing.status_code == 401
    assert bad.json()["title"] == missing.json()["title"]
