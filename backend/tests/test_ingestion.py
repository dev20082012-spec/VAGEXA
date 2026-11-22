import json

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from vagexa.adapters.persistence.models import Transaction
from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings
from vagexa.synthetic.datasets import ground_truth, scenario_bundle

STATEMENT = (
    "line_number,booking_date,booking_time,direction,amount,currency,rail,narration,"
    "counterparty_account,counterparty_ifsc,reference\n"
    "1,2026-03-01,09:00:00,debit,1000.5000,INR,imps,synthetic note,900000000099,SYNB0000001,REF-S1\n"
    "2,2026-03-01,,credit,not-a-number,INR,imps,,900000000098,SYNB0000001,\n"
    "3,2026-03-02,,debit,20.0000,ZZ,imps,,900000000097,SYNB0000001,\n"
)


def _investigator(client: TestClient, name: str = "ingestor") -> None:
    init_engine(load_settings())
    db = open_session()
    try:
        create_user(
            db,
            username=name,
            display_name=name,
            password="correct-horse",
            role_names=["investigator"],
        )
        db.commit()
    finally:
        db.close()
    login = client.post("/api/v1/auth/login", json={"username": name, "password": "correct-horse"})
    assert login.status_code == 200, login.text
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]


def _case(client: TestClient, reference: str = "SYN-INGEST") -> str:
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": reference,
            "title": "Synthetic ingestion",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _upload(client: TestClient, case_id: str, name: str, payload: bytes, **fields: str) -> dict:
    response = client.post(
        f"/api/v1/cases/{case_id}/statements",
        files={"file": (name, payload, "application/octet-stream")},
        data=fields,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _count(case_id: str) -> int:
    init_engine(load_settings())
    db = open_session()
    try:
        return int(
            db.scalar(select(func.count()).select_from(Transaction).where(Transaction.case_id == case_id))
            or 0
        )
    finally:
        db.close()


def test_statement_csv_keeps_invalid_rows_visible(client: TestClient) -> None:
    _investigator(client)
    case_id = _case(client)
    job = _upload(
        client,
        case_id,
        "statement.csv",
        STATEMENT.encode("utf-8"),
        subject_account="900000000090",
        subject_ifsc="SYNB0000001",
    )
    assert job["status"] == "succeeded_with_errors"
    assert job["summary"]["records_valid"] == 1
    assert job["summary"]["records_invalid"] == 2
    issues = client.get(f"/api/v1/jobs/{job['id']}/issues")
    categories = {item["category"] for item in issues.json()["items"]}
    assert "invalid_amount" in categories
    assert "invalid_currency" in categories
    detail = client.get(f"/api/v1/cases/{case_id}/transactions")
    assert detail.json()["items"][0]["amount"] == "1000.5000"


def test_same_bytes_do_not_double_the_transaction_count(client: TestClient) -> None:
    _investigator(client, "replay")
    case_id = _case(client, "SYN-REPLAY")
    payload = scenario_bundle()["normal.csv"]
    first = _upload(client, case_id, "normal.csv", payload)
    second = _upload(client, case_id, "..\\..\\evil.csv", payload)
    assert second["id"] == first["id"]
    assert second["summary"]["idempotent_replay"] is True
    assert _count(case_id) == 2
    listed = client.get(f"/api/v1/cases/{case_id}/transactions")
    assert len(listed.json()["items"]) == 2


def test_duplicate_source_id_is_explained(client: TestClient) -> None:
    _investigator(client, "dups")
    case_id = _case(client, "SYN-DUP")
    job = _upload(client, case_id, "duplicate.csv", scenario_bundle()["duplicate.csv"])
    assert job["summary"]["records_valid"] == 1
    assert job["summary"]["records_duplicate"] == 1
    issues = client.get(f"/api/v1/jobs/{job['id']}/issues").json()["items"]
    assert issues[0]["category"] == "exact_duplicate"
    changed = (
        "source_transaction_id,source_account,source_ifsc,destination_account,destination_ifsc,"
        "amount,currency,timestamp,transaction_type,payment_reference,status\n"
        "D1,900000000051,SYNB0000001,900000000052,SYNB0000001,99.0000,INR,2026-01-19,imps,REF-D1,posted\n"
    )
    again = _upload(client, case_id, "same-id.csv", changed.encode("utf-8"))
    again_issues = client.get(f"/api/v1/jobs/{again['id']}/issues").json()["items"]
    assert again_issues[0]["category"] == "duplicate_source_id"
    assert _count(case_id) == 1


def test_json_transfer_and_chain(client: TestClient) -> None:
    _investigator(client, "json-user")
    case_id = _case(client, "SYN-JSON")
    job = _upload(client, case_id, "normal.json", scenario_bundle()["normal.json"])
    assert job["status"] == "succeeded"
    assert job["summary"]["records_valid"] == 2
    chain = _upload(client, case_id, "mule_chain.csv", scenario_bundle()["mule_chain.csv"])
    assert chain["summary"]["records_valid"] == 3


def test_malformed_json_and_empty_and_encoding(client: TestClient) -> None:
    _investigator(client, "badfiles")
    case_id = _case(client, "SYN-BAD")
    malformed = _upload(client, case_id, "bad.json", b"{")
    assert malformed["status"] == "failed"
    empty = client.post(
        f"/api/v1/cases/{case_id}/statements",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert empty.status_code == 422
    encoded = _upload(client, case_id, "bad.csv", b"\xff\xfe\x00")
    assert encoded["status"] == "failed"
    assert _count(case_id) == 0


def test_unauthorised_and_cross_case_upload(client: TestClient) -> None:
    _investigator(client, "owner")
    case_id = _case(client, "SYN-OWNER")
    client.post("/api/v1/auth/logout")
    init_engine(load_settings())
    db = open_session()
    try:
        create_user = __import__("vagexa.application.auth_service", fromlist=["create_user"]).create_user
        create_user(
            db,
            username="other",
            display_name="other",
            password="correct-horse",
            role_names=["investigator"],
        )
        create_user(
            db,
            username="reader",
            display_name="reader",
            password="correct-horse",
            role_names=["analyst"],
        )
        db.commit()
    finally:
        db.close()
    login = client.post("/api/v1/auth/login", json={"username": "other", "password": "correct-horse"})
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    denied = client.post(
        f"/api/v1/cases/{case_id}/statements",
        files={"file": ("normal.csv", scenario_bundle()["normal.csv"], "text/csv")},
    )
    assert denied.status_code == 404
    client.post("/api/v1/auth/logout")
    analyst = client.post("/api/v1/auth/login", json={"username": "reader", "password": "correct-horse"})
    client.headers["X-CSRF-Token"] = analyst.json()["csrf_token"]
    own = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-READER",
            "title": "Reader",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert own.status_code == 403


def test_ground_truth_is_stable() -> None:
    first = scenario_bundle()
    second = scenario_bundle()
    assert first == second
    truth = ground_truth()
    assert truth["data_classification"] == "synthetic"
    assert truth["expected_inserted"]["mule_chain.csv"] == ["C1", "C2", "C3"]
    assert "finding" not in json.dumps(truth).lower() or "not a finding" in json.dumps(truth)


def test_unexpected_column_is_reported(client: TestClient) -> None:
    _investigator(client, "extra")
    case_id = _case(client, "SYN-EXTRA")
    raw = (
        "source_transaction_id,source_account,source_ifsc,destination_account,destination_ifsc,"
        "amount,currency,timestamp,transaction_type,payment_reference,status,surprise\n"
        "X1,900000000091,SYNB0000001,900000000092,SYNB0000001,1.0000,INR,2026-04-01,upi,REF-X1,posted,hello\n"
    )
    job = _upload(client, case_id, "extra.csv", raw.encode("utf-8"))
    assert "surprise" in job["summary"]["unexpected_columns"]
    assert job["summary"]["records_valid"] == 1
