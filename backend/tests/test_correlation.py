"""correlate.v1 creates a proposal only when a stored key matches."""

from fastapi.testclient import TestClient

from vagexa.intelligence.correlation.correlate import (
    CorrDns,
    CorrDomain,
    CorrHost,
    CorrIp,
    CorrTx,
    correlate,
    hosts_in_text,
)
from vagexa.intelligence.digital.normalise import OVERLAP_LIMITATION
from vagexa.synthetic.datasets import IFSC

STATEMENT = (
    "line_number,booking_date,booking_time,direction,amount,currency,rail,narration,"
    "counterparty_account,counterparty_ifsc,reference\n"
    "1,2026-03-01,09:00:00,debit,10.0000,INR,imps,fee https://syn-a.test/pay,900000000099,SYNB0000001,REF-SAME\n"
    "2,2026-03-01,10:00:00,debit,12.0000,INR,imps,salary,900000000098,SYNB0000001,REF-SAME\n"
)


def test_exact_host_matches_and_a_near_name_does_not() -> None:
    assert hosts_in_text("fee https://syn-a.test/pay") == {"syn-a.test"}
    assert "syn-a.test" not in hosts_in_text("see syn-aa.test today")
    proposals, truncated = correlate(
        [
            CorrTx("t1", "acct", "fee syn-a.test", None, "structured_field"),
            CorrTx("t2", "acct", "salary", None, "structured_field"),
        ],
        [CorrDomain("d1", "syn-a.test")],
        [],
        [],
        [],
    )
    assert truncated is False
    assert [item.pair_key for item in proposals] == ["mentioned_in:t1:d1"]
    assert proposals[0].assertion_kind == "verified"
    assert "not use" in proposals[0].limitation


def test_time_overlap_without_a_key_creates_nothing() -> None:
    proposals, _truncated = correlate(
        [CorrTx("t1", "acct", "salary", None, "unresolved")],
        [CorrDomain("d1", "syn-a.test")],
        [CorrIp("ip1", "203.0.113.50")],
        [CorrDns("o1", "d1", "ip1")],
        [],
    )
    assert proposals == []


def test_shared_address_is_co_occurrence_not_ownership() -> None:
    proposals, _truncated = correlate(
        [],
        [CorrDomain("d1", "syn-a.test"), CorrDomain("d2", "syn-b.test")],
        [CorrIp("ip1", "203.0.113.50")],
        [CorrDns("o1", "d1", "ip1"), CorrDns("o2", "d2", "ip1")],
        [
            CorrHost("h1", "ip2", "Synthetic Public Resolver"),
            CorrHost("h2", "ip3", "Synthetic Public Resolver"),
        ],
    )
    kinds = {item.rel_type for item in proposals}
    assert kinds == {"infrastructure_overlap"}
    assert all(item.limitation == OVERLAP_LIMITATION for item in proposals)
    assert all(item.assertion_kind == "verified" for item in proposals)


def test_same_structured_reference_is_one_pair() -> None:
    proposals, _truncated = correlate(
        [
            CorrTx("a", "left", "", "UTR1", "structured_field"),
            CorrTx("b", "right", "", "UTR1", "structured_field"),
            CorrTx("c", "other", "", "UTR1", "narration_pattern"),
        ],
        [],
        [],
        [],
        [],
    )
    assert len(proposals) == 1
    assert proposals[0].rel_type == "same_payment"
    assert proposals[0].support == (("transaction", "a"), ("transaction", "b"))


def _user(client: TestClient, name: str, role: str) -> str:
    from vagexa.adapters.persistence.session import init_engine, open_session
    from vagexa.application.auth_service import create_user
    from vagexa.config import load_settings

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


def test_api_correlation_is_reviewable_and_not_doubled(client: TestClient) -> None:
    _user(client, "corr-owner", "investigator")
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-CORR",
            "title": "Correlation",
            "opened_on": "2026-03-01",
            "data_classification": "synthetic",
        },
    )
    case_id = created.json()["id"]
    uploaded = client.post(
        f"/api/v1/cases/{case_id}/statements",
        files={"file": ("narration.csv", STATEMENT.encode(), "text/csv")},
        data={"subject_account": "900000000001", "subject_ifsc": IFSC},
    )
    assert uploaded.status_code == 201, uploaded.text
    for domain in ("syn-a.test", "syn-b.test"):
        observed = client.post(
            f"/api/v1/cases/{case_id}/observations",
            json={
                "kind": "dns",
                "domain": domain,
                "rrtype": "A",
                "rdata": "203.0.113.50",
                "observed_at": "2026-03-01T09:00:00Z",
            },
        )
        assert observed.status_code == 201, observed.text
    first = client.post(f"/api/v1/cases/{case_id}/correlations")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["inserted"] >= 1
    mentioned = [item for item in body["items"] if item["rel_type"] == "mentioned_in"]
    assert len(mentioned) == 1
    assert mentioned[0]["assertion_kind"] == "verified"
    assert mentioned[0]["status"] == "proposed"
    overlap = [item for item in body["items"] if item["rel_type"] == "infrastructure_overlap"]
    assert overlap
    assert overlap[0]["limitation"] == OVERLAP_LIMITATION
    second = client.post(f"/api/v1/cases/{case_id}/correlations")
    assert second.json()["inserted"] == 0
    assert second.json()["already_present"] == body["inserted"]
    graph = client.get(f"/api/v1/cases/{case_id}/graph")
    assert any(edge["kind"] == "mentioned_in" for edge in graph.json()["edges"])
    analyst = _user(client, "corr-analyst", "analyst")
    admin = _user(client, "corr-admin", "administrator")
    login = client.post("/api/v1/auth/login", json={"username": "corr-admin", "password": "correct-horse"})
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (
        client.post(
            f"/api/v1/cases/{case_id}/assignments",
            json={"user_id": analyst, "case_role": "analyst"},
        ).status_code
        == 201
    )
    analyst_login = client.post(
        "/api/v1/auth/login", json={"username": "corr-analyst", "password": "correct-horse"}
    )
    client.headers["X-CSRF-Token"] = analyst_login.json()["csrf_token"]
    assert (
        client.post(f"/api/v1/relationships/{mentioned[0]['id']}/confirm", json={"note": "seen"}).status_code
        == 403
    )
    owner = client.post("/api/v1/auth/login", json={"username": "corr-owner", "password": "correct-horse"})
    client.headers["X-CSRF-Token"] = owner.json()["csrf_token"]
    decided = client.post(
        f"/api/v1/relationships/{mentioned[0]['id']}/confirm",
        json={"note": "The narration contains the host."},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "confirmed"
    assert decided.json()["assertion_kind"] == "verified"
    assert decided.json()["reviews"][0]["reason"] == "The narration contains the host."
    again = client.post(f"/api/v1/relationships/{mentioned[0]['id']}/confirm", json={"note": "again"})
    assert again.status_code == 409
    outsider = _user(client, "corr-outsider", "investigator")
    assert outsider
    assert client.get(f"/api/v1/cases/{case_id}/relationships").status_code == 404
    assert admin
