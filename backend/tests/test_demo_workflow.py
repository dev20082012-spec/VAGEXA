"""SYN-DEMO end to end, from the seed command to the API. Expectations come from demo.ground_truth()."""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from vagexa.adapters.persistence.models import (
    Account,
    AnalyticalRun,
    Case,
    DnsObservation,
    DomainName,
    Finding,
    GatewayRecord,
    Relationship,
    Transaction,
)
from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.api.main import create_app
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings
from vagexa.demo_seed import seed_demo
from vagexa.intelligence.correlation.classify import RelView, classify
from vagexa.intelligence.digital.normalise import OVERLAP_LIMITATION
from vagexa.synthetic.demo import REFERENCE, ground_truth

TRUTH = ground_truth()


def _user(name: str, role: str) -> str:
    init_engine(load_settings())
    db = open_session()
    try:
        user = create_user(db, username=name, display_name=name, password="correct-horse", role_names=[role])
        db.commit()
        return str(user.id)
    finally:
        db.close()


def _seed(username: str) -> str:
    settings = load_settings()
    init_engine(settings)
    db = open_session()
    try:
        result = seed_demo(db, settings, username)
        db.commit()
        return str(result["case_id"])
    finally:
        db.close()


def _counts() -> dict[str, int]:
    init_engine(load_settings())
    db = open_session()
    try:

        def count(model: type) -> int:
            return int(db.scalar(select(func.count()).select_from(model)) or 0)

        return {
            "cases": int(
                db.scalar(select(func.count()).select_from(Case).where(Case.reference == REFERENCE)) or 0
            ),
            "transactions": count(Transaction),
            "dns": count(DnsObservation),
            "gateway": count(GatewayRecord),
            "relationships": count(Relationship),
            "runs": count(AnalyticalRun),
            "findings": count(Finding),
        }
    finally:
        db.close()


def _login(client: TestClient, username: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "correct-horse"})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]


def test_seed_is_repeatable_and_the_workflow_matches_ground_truth(client: TestClient) -> None:
    _user("demo-lead", "investigator")
    case_id = _seed("demo-lead")
    first = _counts()
    assert _seed("demo-lead") == case_id
    assert _counts() == first
    assert first["cases"] == 1
    assert first["transactions"] == TRUTH["transactions"]
    assert first["gateway"] == TRUTH["gateway_records"]
    assert first["relationships"] == TRUTH["relationships"]
    assert first["findings"] == TRUTH["findings"]

    _login(client, "demo-lead")
    summary = client.get(f"/api/v1/cases/{case_id}/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["case"]["reference"] == REFERENCE
    assert body["case"]["title"] == TRUTH["title"]
    assert body["case"]["status"] == TRUTH["status"]
    assert body["case"]["opened_on"] == TRUTH["opened_on"]
    assert body["case"]["data_classification"] == "synthetic"
    assert "Synthetic demonstration data" in body["synthetic_notice"]
    assert body["counts"]["transactions"] == TRUTH["transactions"]
    assert body["counts"]["statements"] == TRUTH["statements"]
    assert body["counts"]["dns_observations"] == TRUTH["dns_observations"]
    assert body["counts"]["hosting_observations"] == TRUTH["hosting_observations"]
    assert body["counts"]["gateway_records"] == TRUTH["gateway_records"]
    assert body["counts"]["findings"] == TRUTH["findings"]
    assert body["counts"]["relationships"] == TRUTH["relationships"]
    lowered = summary.text.lower()
    assert "ground" not in lowered
    assert "victim" not in lowered
    assert body["cross_domain_by_classification"] == TRUTH["cross_domain_by_classification"]
    assert body["overlap_count"] == TRUTH["overlap_count"]
    residual = body["latest_trace"]["residuals"][0]
    assert [residual["account_masked"], residual["reason"], residual["amount"]] == TRUTH["trace_residual"]
    assert sorted([item["code"], item["account_masked"]] for item in body["indicators"]) == sorted(
        TRUTH["indicators"]
    )

    listed = client.get(f"/api/v1/cases/{case_id}/transactions", params={"limit": 100})
    assert listed.status_code == 200
    rows = listed.json()["items"]
    assert len(rows) == TRUTH["transactions"]
    debits = sum((Decimal(row["amount"]) for row in rows if row["direction"] == "debit"), Decimal("0"))
    credits = sum((Decimal(row["amount"]) for row in rows if row["direction"] == "credit"), Decimal("0"))
    assert f"{debits:.4f}" == TRUTH["statement_debits"]
    assert f"{credits:.4f}" == TRUTH["statement_credits"]
    opening = TRUTH["opening_transfer"]
    opening_row = next(
        row for row in rows if row["source_transaction_id"] == opening["source_transaction_id"]
    )
    assert opening_row["account_masked"] == opening["from"]
    assert opening_row["counterparty_masked"] == opening["to"]
    assert opening_row["amount"] == opening["amount"]
    assert opening_row["currency"] == opening["currency"]
    assert opening_row["reference_raw"] == opening["reference"]
    assert opening_row["booking_date"] == opening["booking_date"]
    assert opening_row["booking_time"] == opening["booking_time"]
    disputed = next(row for row in rows if row["source_transaction_id"] == "DEMO-D-OUT")
    assert disputed["amount"] == TRUTH["contradicted_gateways"]["amount"]

    def record(source_id: str) -> dict[str, object]:
        row = next(item for item in rows if item["source_transaction_id"] == source_id)
        opened = client.get(f"/api/v1/cases/{case_id}/evidence/transaction/{row['id']}")
        assert opened.status_code == 200, opened.text
        body = opened.json()
        assert body["data_classification"] == "synthetic"
        return body["record"]

    missing = TRUTH["missing_identifier"]
    near_name = record(str(missing["source_transaction_id"]))
    assert missing["host"] in str(near_name["narration"])
    disputed_record = record("DEMO-D-OUT")
    assert "syn-" not in str(disputed_record["narration"])

    activity = client.get(f"/api/v1/cases/{case_id}/activity").json()["items"]
    by_account = {item["account_masked"]: item for item in activity}
    for masked, expected in TRUTH["activity"].items():
        actual = by_account[masked]
        for field, value in expected.items():
            assert actual[field] == value, (masked, field)

    trace_id = body["latest_trace"]["id"]
    trace = client.get(f"/api/v1/traces/{trace_id}").json()
    hops = [
        [flow["from_account_masked"], flow["to_account_masked"], flow["layer_to"]] for flow in trace["flows"]
    ]
    assert hops == TRUTH["trace_layers"]
    traced = {account for hop in hops for account in hop[:2]}
    assert TRUTH["not_attributed_at_horizon_3"] not in traced
    for account in TRUTH["not_in_trace"]:
        assert account not in traced, account
    assert trace["flows"][0]["reference"] == "UTRSYN0001"
    assert trace["flows"][0]["amount"] == TRUTH["opening_transfer"]["amount"]
    assert trace["path_summary"]["holding_accounts_masked"] == ["****0013"]
    assert "PASS_THROUGH" not in {item["code"] for item in body["indicators"]}

    observations = client.get(f"/api/v1/cases/{case_id}/observations").json()
    history = sorted(row["rdata"] for row in observations["dns"] if row["domain"] == "syn-a.test")
    assert history == TRUTH["dns_history"]["syn-a.test"]

    gateway = client.get(f"/api/v1/cases/{case_id}/gateway-records").json()["items"]
    assert len(gateway) == TRUTH["gateway_records"]
    assert all(item["data_classification"] == "synthetic" for item in gateway)
    by_source = {item["record"]["source_record_id"]: item for item in gateway}
    primary_gateway = by_source["SYN-PG-0001"]
    assert primary_gateway["record"]["merchant_domain"] == "syn-a.test"
    assert primary_gateway["record"]["payee_account_masked"] == "****0011"
    conflict = TRUTH["contradicted_gateways"]
    for source_id, domain in zip(conflict["source_record_ids"], conflict["domains"], strict=True):
        stored = by_source[source_id]["record"]
        assert stored["merchant_domain"] == domain
        assert stored["payment_reference"] == conflict["reference"]
        assert stored["amount"] == conflict["amount"]
        assert stored["payee_account_masked"] == conflict["account"]

    relationships = client.get(f"/api/v1/cases/{case_id}/relationships").json()["items"]
    assert len(relationships) == TRUTH["relationships"]
    by_type: dict[str, list[dict]] = {}
    for item in relationships:
        by_type.setdefault(item["rel_type"], []).append(item)
    merchant = [item for item in by_type["gateway_merchant"] if item["classification"] == "CORROBORATED"]
    assert len(merchant) == 1
    expected = TRUTH["gateway_merchant"]
    assert [merchant[0]["from_label"], merchant[0]["to_label"], merchant[0]["classification"]] == [
        expected["account"],
        expected["domain"],
        expected["classification"],
    ]
    rivals = [item for item in by_type["gateway_merchant"] if item["classification"] == "CONTRADICTED"]
    assert sorted(item["to_label"] for item in rivals) == conflict["domains"]
    assert {item["from_label"] for item in rivals} == {conflict["account"]}
    assert all(item["status"] == "proposed" for item in rivals)
    assert all(item["method_version"] == "correlate.v2" for item in by_type["gateway_merchant"])
    assert merchant[0]["assertion_kind"] == "verified"
    assert merchant[0]["status"] == "proposed"
    assert "does not identify who operates the domain" in merchant[0]["limitation"]
    assert any(item["field"] == "processed_at" for item in merchant[0]["temporal_context"])
    mention = by_type["mentioned_in"]
    assert [[item["from_label"], item["to_label"], item["classification"]] for item in mention] == [
        [
            TRUTH["mentioned_in"]["account"],
            TRUTH["mentioned_in"]["domain"],
            TRUTH["mentioned_in"]["classification"],
        ]
    ]
    assert len(by_type["same_payment"]) == TRUTH["same_payment_pairs"]
    overlaps = by_type["infrastructure_overlap"]
    assert all(item["classification"] == TRUTH["overlap_classification"] for item in overlaps)
    assert all(item["limitation"] == OVERLAP_LIMITATION for item in overlaps)
    assert any(
        sorted([item["from_label"], item["to_label"]]) == TRUTH["overlap_domains"] for item in overlaps
    )
    for name in TRUTH["no_account_link"]:
        assert not any(
            item["to_label"] == name and item["from_kind"] == "account" for item in relationships
        ), name
    temporal = TRUTH["temporal_only"]
    assert not any(
        item["from_label"] == temporal["account"] and item["to_label"] == temporal["domain"]
        for item in relationships
    )

    evidence = client.get(f"/api/v1/relationships/{merchant[0]['id']}/evidence").json()["items"]
    kinds = sorted(item["object_kind"] for item in evidence)
    assert kinds == ["gateway_record", "transaction", "transaction"]
    narration = next(item for item in evidence if item["record"].get("source_transaction_id") == "DEMO-V-1")
    assert "syn-a.test" in narration["record"]["narration"]
    assert all(item["data_classification"] == "synthetic" for item in evidence)

    graph = client.get(f"/api/v1/cases/{case_id}/graph").json()
    node_ids = {node["id"] for node in graph["nodes"]}
    init_engine(load_settings())
    db = open_session()
    try:
        for node in graph["nodes"]:
            if node["kind"] == "account":
                assert db.get(Account, uuid.UUID(node["id"])) is not None
            if node["kind"] == "domain":
                assert db.get(DomainName, uuid.UUID(node["id"].split(":", 1)[1])) is not None
    finally:
        db.close()
    for edge in graph["edges"]:
        assert edge["from"] in node_ids and edge["to"] in node_ids
        assert edge["support"], edge["id"]
    labels = {node["id"]: node["label"] for node in graph["nodes"]}
    bridge = [
        edge
        for edge in graph["edges"]
        if edge["kind"] == "gateway_merchant" and edge["classification"] == "CORROBORATED"
    ]
    assert len(bridge) == 1
    contradicted_edges = [
        edge
        for edge in graph["edges"]
        if edge["kind"] == "gateway_merchant" and edge["classification"] == "CONTRADICTED"
    ]
    assert len(contradicted_edges) == 2
    for item in bridge[0]["support"]:
        opened = client.get(f"/api/v1/cases/{case_id}/evidence/{item['object_kind']}/{item['object_id']}")
        assert opened.status_code == 200, opened.text
    opening_edge = next(
        edge
        for edge in graph["edges"]
        if edge["kind"] == "transfer" and opening_row["id"] in edge["source_transaction_ids"]
    )
    assert labels[opening_edge["from"]] == TRUTH["opening_transfer"]["from"]
    assert labels[opening_edge["to"]] == TRUTH["opening_transfer"]["to"]
    assert opening_edge["amount"] == TRUTH["opening_transfer"]["amount"]
    assert opening_edge["currency"] == TRUTH["opening_transfer"]["currency"]
    disputed_edge = next(
        edge
        for edge in graph["edges"]
        if edge["kind"] == "transfer" and disputed["id"] in edge["source_transaction_ids"]
    )
    assert labels[disputed_edge["from"]] == "****0070"
    assert labels[disputed_edge["to"]] == "****0071"
    assert disputed_edge["amount"] == "2500.0000"
    syn_b = next(node["id"] for node in graph["nodes"] if node["label"] == "syn-b.test")
    assert not any(
        edge["to"] == syn_b and edge["kind"] in {"gateway_merchant", "mentioned_in"}
        for edge in graph["edges"]
    )

    findings = client.get(f"/api/v1/cases/{case_id}/findings").json()["items"]
    assert len(findings) == TRUTH["findings"]
    assert all(str(item["limitations"]).strip() for item in findings)
    assert all(item["method_version"] for item in findings)

    _user("demo-outsider", "investigator")
    _login(client, "demo-outsider")
    assert client.get(f"/api/v1/cases/{case_id}/summary").status_code == 404
    assert client.get(f"/api/v1/cases/{case_id}/graph").status_code == 404
    assert client.get(f"/api/v1/relationships/{merchant[0]['id']}/evidence").status_code == 404
    first_support = bridge[0]["support"][0]
    assert (
        client.get(
            f"/api/v1/cases/{case_id}/evidence/{first_support['object_kind']}/{first_support['object_id']}"
        ).status_code
        == 404
    )


def test_a_new_process_reads_the_same_case() -> None:
    _user("demo-restart", "investigator")
    case_id = _seed("demo-restart")
    for _attempt in range(2):
        with TestClient(create_app(load_settings())) as fresh:
            _login(fresh, "demo-restart")
            body = fresh.get(f"/api/v1/cases/{case_id}/summary").json()
            assert body["case"]["reference"] == REFERENCE
            assert body["counts"]["transactions"] == TRUTH["transactions"]


def test_classification_marks_conflicting_gateway_records() -> None:
    rows = [
        RelView("g1", "gateway_merchant", "verified", "domain-a", frozenset({"tx"})),
        RelView("g2", "gateway_merchant", "verified", "domain-b", frozenset({"tx"})),
        RelView("m1", "mentioned_in", "verified", "domain-c", frozenset({"other"})),
        RelView("o1", "infrastructure_overlap", "verified", "domain-d", frozenset()),
    ]
    result = classify(rows)
    assert result["g1"].classification == "CONTRADICTED"
    assert result["g2"].classification == "CONTRADICTED"
    assert result["m1"].classification == "DIRECTLY_SUPPORTED"
    assert result["o1"].classification == "UNRESOLVED"
