import json
from pathlib import Path

from fastapi.testclient import TestClient

from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings

SCHEMA = json.loads(
    Path(__file__).resolve().parents[2].joinpath("contracts", "case.schema.json").read_text(encoding="utf-8")
)


def test_created_case_matches_shared_schema(client: TestClient) -> None:
    init_engine(load_settings())
    db = open_session()
    try:
        create_user(
            db,
            username="contract",
            display_name="Contract",
            password="correct-horse",
            role_names=["investigator"],
        )
        db.commit()
    finally:
        db.close()
    login = client.post("/api/v1/auth/login", json={"username": "contract", "password": "correct-horse"})
    assert login.status_code == 200
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    response = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-C",
            "title": "Contract case",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert response.status_code == 201
    body = response.json()
    for field in SCHEMA["required"]:
        assert field in body
