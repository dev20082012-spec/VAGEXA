"""API checks for fifo.v1, indicators, and case isolation."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from vagexa.adapters.persistence.models import TraceFlow
from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings
from vagexa.synthetic.datasets import IFSC, analysis_ground_truth, intelligence_statements


def _user(client: TestClient, name: str, role: str) -> str:
    init_engine(load_settings())
    db = open_session()
    try:
        user = create_user(db, username=name, display_name=name, password="correct-horse", role_names=[role])
        db.commit()
        user_id = str(user.id)
    finally:
        db.close()
    login = client.post("/api/v1/auth/login", json={"username": name, "password": "correct-horse"})
    assert login.status_code == 200, login.text
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    return user_id


def _case(client: TestClient) -> str:
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-ANALYSIS",
            "title": "Synthetic analysis",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def _load(client: TestClient, case_id: str) -> None:
    for subject, name, payload in intelligence_statements():
        response = client.post(
            f"/api/v1/cases/{case_id}/statements",
            files={"file": (name, payload, "text/csv")},
            data={"subject_account": subject, "subject_ifsc": IFSC},
        )
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "succeeded"


def _seed(client: TestClient, case_id: str) -> str:
    listed = client.get(f"/api/v1/cases/{case_id}/transactions", params={"source_transaction_id": "S1-V"})
    assert listed.status_code == 200, listed.text
    return str(listed.json()["items"][0]["id"])


def _flow_count(run_id: str) -> int:
    init_engine(load_settings())
    db = open_session()
    try:
        return int(
            db.scalar(
                select(func.count()).select_from(TraceFlow).where(TraceFlow.analytical_run_id == run_id)
            )
            or 0
        )
    finally:
        db.close()


def test_horizon_three_matches_ground_truth_and_repeat_does_not_double(client: TestClient) -> None:
    truth = analysis_ground_truth()
    _user(client, "analyst-runner", "investigator")
    case_id = _case(client)
    _load(client, case_id)
    seed = _seed(client, case_id)
    first = client.post(
        f"/api/v1/cases/{case_id}/traces",
        json={"seed_transaction_ids": [seed], "policy": "fifo", "policy_version": "fifo.v1", "max_layer": 3},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["status"] == "succeeded"
    assert body["method_version"] == "fifo.v1"
    assert [(item["layer_to"], item["amount"]) for item in body["flows"]] == [
        (1, "100000.0000"),
        (2, "100000.0000"),
        (3, "100000.0000"),
    ]
    assert body["residuals"][0]["reason"] == "outside_horizon"
    assert body["residuals"][0]["account_masked"] == "****0013"
    assert all(item["to_account_masked"] != "****0019" for item in body["flows"])
    assert "not an attributed beneficiary" in body["limitations"]
    assert all(item["to_account_masked"] != "****0051" for item in body["flows"])
    assert body["flows"][1]["hours_after_previous"] == "0.3333"
    second = client.post(
        f"/api/v1/cases/{case_id}/traces",
        json={"seed_transaction_ids": [seed], "max_layer": 3, "currency": "INR"},
    )
    assert second.status_code == 200
    assert second.json()["output_hash"] == body["output_hash"]
    assert second.json()["id"] != body["id"]
    assert len(second.json()["flows"]) == 3
    deeper = client.post(
        f"/api/v1/cases/{case_id}/traces",
        json={"seed_transaction_ids": [seed], "max_layer": 4},
    )
    assert deeper.json()["flows"][-1]["to_account_masked"] == "****0019"
    assert truth["pass_through_at_default_ratio"] is False
    indicators = client.post(
        f"/api/v1/cases/{case_id}/indicator-runs",
        json={"window_start": "2026-01-16", "window_end": "2026-01-17", "currency": "INR"},
    )
    assert indicators.status_code == 200, indicators.text
    codes = {item["code"] for item in indicators.json()["items"]}
    assert codes == {"FAN_IN", "FAN_OUT"}
    assert all(item["account_masked"] == "****0030" for item in indicators.json()["items"])
    assert all(
        "rule match" in item["limitations"].lower() or "rule match" in item["limitations"]
        for item in indicators.json()["items"]
    )
    passed = client.post(
        f"/api/v1/cases/{case_id}/indicator-runs",
        json={
            "window_start": "2026-01-16",
            "window_end": "2026-01-17",
            "pass_through_ratio": "0.50",
            "pass_through_dwell_hours": "48",
            "currency": "INR",
        },
    )
    assert "PASS_THROUGH" in {item["code"] for item in passed.json()["items"]}
    findings = client.get(f"/api/v1/cases/{case_id}/findings")
    assert findings.status_code == 200
    assert any(item["support_transaction_ids"] for item in findings.json()["items"])
    assert all(item["limitations"] for item in findings.json()["items"])
    summary = client.get(f"/api/v1/cases/{case_id}/financial-summary")
    assert summary.status_code == 200
    assert summary.json()["transaction_count"] > 0
    assert summary.json()["data_classification"] == "synthetic"
    assert "INR" in summary.json()["currencies"]
    assert "USD" not in summary.json()["currencies"]
    activity = client.get(f"/api/v1/cases/{case_id}/activity", params={"currency": "INR"})
    victim = next(item for item in activity.json()["items"] if item["account_masked"] == "****0001")
    walk = client.post(
        f"/api/v1/cases/{case_id}/statement-walks",
        json={
            "start_account_id": victim["account_id"],
            "direction": "forward",
            "max_layer": 3,
            "currency": "INR",
            "window_start": "2026-01-15",
            "window_end": "2026-01-15",
        },
    )
    assert walk.status_code == 200, walk.text
    assert "Not a FIFO allocation" in walk.json()["limitations"]
    destinations = [hop["to_account_masked"] for hop in walk.json()["paths"][0]["hops"]]
    assert "****0019" not in destinations
    assert (
        client.post(
            f"/api/v1/cases/{case_id}/traces", json={"seed_transaction_ids": [seed], "max_layer": 6}
        ).status_code
        == 422
    )


def _login(client: TestClient, username: str) -> None:
    login = client.post("/api/v1/auth/login", json={"username": username, "password": "correct-horse"})
    assert login.status_code == 200, login.text
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]


def test_auditor_cannot_run_and_another_case_cannot_read(client: TestClient) -> None:
    _user(client, "owner-an", "investigator")
    case_id = _case(client)
    _load(client, case_id)
    seed = _seed(client, case_id)
    created = client.post(
        f"/api/v1/cases/{case_id}/traces", json={"seed_transaction_ids": [seed], "max_layer": 3}
    )
    assert created.status_code == 200, created.text
    trace_id = created.json()["id"]
    _user(client, "admin-an", "administrator")
    auditor = _user(client, "audit-an", "auditor")
    analyst = _user(client, "analyst-an", "analyst")
    _user(client, "outsider-an", "investigator")
    _login(client, "admin-an")
    assert (
        client.post(
            f"/api/v1/cases/{case_id}/assignments", json={"user_id": auditor, "case_role": "auditor"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/cases/{case_id}/assignments", json={"user_id": analyst, "case_role": "analyst"}
        ).status_code
        == 201
    )
    _login(client, "audit-an")
    denied = client.post(
        f"/api/v1/cases/{case_id}/traces", json={"seed_transaction_ids": [seed], "max_layer": 3}
    )
    assert denied.status_code == 403
    assert client.get(f"/api/v1/traces/{trace_id}").status_code == 200
    _login(client, "analyst-an")
    allowed = client.post(
        f"/api/v1/cases/{case_id}/traces", json={"seed_transaction_ids": [seed], "max_layer": 1}
    )
    assert allowed.status_code == 200, allowed.text
    _login(client, "outsider-an")
    assert client.get(f"/api/v1/traces/{trace_id}").status_code == 404


def test_conservation_failure_stores_no_flows(client: TestClient, monkeypatch) -> None:
    from vagexa.intelligence.financial.fifo import TraceResult

    def failed(*_args: object, **_kwargs: object) -> TraceResult:
        return TraceResult(status="failed", error_code="conservation", limitations="Conservation failed.")

    monkeypatch.setattr("vagexa.application.analysis_service.trace", failed)
    _user(client, "owner-fail", "investigator")
    case_id = _case(client)
    _load(client, case_id)
    seed = _seed(client, case_id)
    response = client.post(
        f"/api/v1/cases/{case_id}/traces", json={"seed_transaction_ids": [seed], "max_layer": 3}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
    assert response.json()["flows"] == []
    assert _flow_count(response.json()["id"]) == 0
