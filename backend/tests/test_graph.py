"""Derived graph. Ground truth is the chain shape, not a picture of circles."""

from datetime import date, time
from decimal import Decimal

from fastapi.testclient import TestClient

from vagexa.intelligence.graph.build import GraphFlow, GraphLeg, GraphResidual, build_graph
from vagexa.synthetic.datasets import IFSC, intelligence_statements

D = date(2026, 1, 15)


def _leg(
    tx: str,
    account: str,
    direction: str,
    counterparty: str,
    reference: str,
    amount: str = "100000.0000",
    resolution: str = "structured_field",
    rail: str = "imps",
    line_time: str = "09:00:00",
) -> GraphLeg:
    return GraphLeg(
        tx,
        account,
        direction,
        counterparty,
        resolution,
        Decimal(amount),
        "INR",
        D,
        time.fromisoformat(line_time),
        f"prov-{tx}",
        f"ev-{tx}",
        reference,
        rail,
        "ingest.v1",
    )


def _flow(flow_id: str, source: str, target: str, layer: int, tx: str) -> GraphFlow:
    return GraphFlow(
        flow_id,
        source,
        target,
        None,
        Decimal("100000.0000"),
        "INR",
        layer,
        "verified",
        "reference_join",
        "fifo.v1",
        tx,
        "run-1",
        D,
    )


def _chain() -> tuple[list[GraphLeg], list[GraphFlow], list[GraphResidual]]:
    legs = [
        _leg("V", "A", "debit", "I1", "R1", line_time="09:00:00"),
        _leg("I1C", "I1", "credit", "A", "R1", line_time="09:01:00"),
        _leg("I1D", "I1", "debit", "I2", "R2", line_time="09:20:00"),
        _leg("I2C", "I2", "credit", "I1", "R2", line_time="09:21:00"),
        _leg("I2D", "I2", "debit", "I3", "R3", line_time="10:00:00"),
        _leg("I3C", "I3", "credit", "I2", "R3", line_time="10:01:00"),
        _leg("I3D", "I3", "debit", "B", "R4", line_time="11:00:00"),
        _leg("BC", "B", "credit", "I3", "R4", line_time="11:01:00"),
    ]
    flows = [
        _flow("F1", "A", "I1", 1, "V"),
        _flow("F2", "I1", "I2", 2, "I1D"),
        _flow("F3", "I2", "I3", 3, "I2D"),
    ]
    residuals = [GraphResidual("I3", Decimal("100000.0000"), "INR", "outside_horizon", "run-1")]
    return legs, flows, residuals


def test_horizon_three_keeps_the_statement_to_b_and_does_not_allocate_it() -> None:
    legs, flows, residuals = _chain()
    graph = build_graph(
        legs,
        flows,
        residuals,
        labels={"A": "****0001", "I1": "****0011", "I2": "****0012", "I3": "****0013", "B": "****0019"},
        data_classification="synthetic",
        focus=None,
        max_hops=3,
    )
    allocated = sorted(
        (edge for edge in graph.edges if edge.layer_to is not None),
        key=lambda edge: edge.layer_to or 0,
    )
    assert [(edge.source, edge.target, edge.layer_to) for edge in allocated] == [
        ("A", "I1", 1),
        ("I1", "I2", 2),
        ("I2", "I3", 3),
    ]
    statement_to_b = next(edge for edge in graph.edges if edge.target == "B")
    assert statement_to_b.layer_to is None
    assert statement_to_b.assertion_kind == "verified"
    assert statement_to_b.source_transaction_ids
    i3 = next(node for node in graph.nodes if node.id == "I3")
    assert i3.residuals[0]["reason"] == "outside_horizon"
    assert "not an attributed beneficiary" in graph.limitations


def test_focus_drops_nodes_beyond_the_hop_cap() -> None:
    legs, flows, residuals = _chain()
    graph = build_graph(
        legs, flows, residuals, labels={}, data_classification="synthetic", focus="A", max_hops=1
    )
    assert {node.id for node in graph.nodes} == {"A", "I1"}
    assert graph.truncated is True


def test_duplicate_transaction_is_one_edge() -> None:
    leg = _leg("V", "A", "debit", "I1", "R1")
    graph = build_graph(
        [leg, leg], [], [], labels={}, data_classification="synthetic", focus=None, max_hops=3
    )
    assert len(graph.edges) == 1
    assert graph.edges[0].id == "tx:V"


def test_similar_identifiers_stay_separate_nodes() -> None:
    legs = [
        _leg("T1", "100000000001", "debit", "100000000011", "S1", amount="10.0000"),
        _leg("T2", "100000000002", "debit", "100000000012", "S2", amount="10.0000"),
    ]
    graph = build_graph(legs, [], [], labels={}, data_classification="synthetic", focus=None, max_hops=3)
    assert len(graph.components) == 2
    assert {node.id for node in graph.nodes} == {
        "100000000001",
        "100000000011",
        "100000000002",
        "100000000012",
    }


def test_narration_edge_is_inferred_and_a_partial_allocation_stays_beside_it() -> None:
    leg = _leg("N", "A", "debit", "B", "NR", resolution="narration_pattern", amount="80.0000")
    flow = GraphFlow(
        "F",
        "A",
        "B",
        None,
        Decimal("40.0000"),
        "INR",
        1,
        "inferred",
        "narration_extractor",
        "fifo.v1",
        "N",
        "run-1",
        D,
    )
    graph = build_graph([leg], [flow], [], labels={}, data_classification="synthetic", focus=None, max_hops=3)
    assert {edge.amount for edge in graph.edges} == {"80.0000", "40.0000"}
    assert all(edge.assertion_kind == "inferred" for edge in graph.edges)


def test_cash_exit_is_not_an_account() -> None:
    leg = _leg("C", "A", "debit", "B", "CASH", rail="cash", amount="10.0000")
    graph = build_graph([leg], [], [], labels={}, data_classification="synthetic", focus=None, max_hops=3)
    assert graph.nodes[0].kind == "account" or any(node.kind == "cash_exit" for node in graph.nodes)
    exit_node = next(node for node in graph.nodes if node.kind == "cash_exit")
    assert exit_node.label == "Cash exit"
    assert graph.edges[0].target == exit_node.id


def test_shortest_path_stops_at_the_hop_cap() -> None:
    legs, flows, residuals = _chain()
    short = build_graph(
        legs,
        flows,
        residuals,
        labels={},
        data_classification="synthetic",
        focus=None,
        max_hops=3,
        path_from="A",
        path_to="I2",
    )
    assert short.path == ["A", "I1", "I2"]
    blocked = build_graph(
        legs,
        flows,
        residuals,
        labels={},
        data_classification="synthetic",
        focus=None,
        max_hops=1,
        path_from="A",
        path_to="I3",
    )
    assert blocked.path is None
    assert blocked.path_reason == "beyond_hops"


def test_two_thousand_edges_stay_bounded() -> None:
    import time as clock

    legs = [
        _leg(f"T{index}", f"S{index}", "debit", f"D{index}", f"R{index}", amount="1.0000")
        for index in range(2000)
    ]
    started = clock.perf_counter()
    graph = build_graph(legs, [], [], labels={}, data_classification="synthetic", focus="S0", max_hops=1)
    assert clock.perf_counter() - started < 2
    assert len(graph.edges) == 1
    assert graph.truncated is True


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


def _login(client: TestClient, username: str) -> None:
    login = client.post("/api/v1/auth/login", json={"username": username, "password": "correct-horse"})
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]


def test_api_graph_matches_the_chain_and_hides_the_other_case(client: TestClient) -> None:
    _user(client, "graph-owner", "investigator")
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-GRAPH",
            "title": "Graph case",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    case_id = created.json()["id"]
    for subject, name, payload in intelligence_statements():
        response = client.post(
            f"/api/v1/cases/{case_id}/statements",
            files={"file": (name, payload, "text/csv")},
            data={"subject_account": subject, "subject_ifsc": IFSC},
        )
        assert response.status_code == 201, response.text
    seed = client.get(
        f"/api/v1/cases/{case_id}/transactions", params={"source_transaction_id": "S1-V"}
    ).json()["items"][0]["id"]
    trace = client.post(
        f"/api/v1/cases/{case_id}/traces", json={"seed_transaction_ids": [seed], "max_layer": 3}
    )
    assert trace.status_code == 200, trace.text
    graph = client.get(f"/api/v1/cases/{case_id}/graph", params={"max_hops": 3})
    assert graph.status_code == 200, graph.text
    body = graph.json()
    allocated = [edge for edge in body["edges"] if edge["layer_to"] is not None]
    assert sorted(edge["layer_to"] for edge in allocated) == [1, 2, 3]
    assert all(edge["to"] for edge in allocated)
    labels = {node["id"]: node["label"] for node in body["nodes"]}
    assert all(labels[edge["to"]] != "****0019" for edge in allocated)
    beneficiary = next(node for node in body["nodes"] if node["label"] == "****0013")
    assert beneficiary["residuals"][0]["reason"] == "outside_horizon"
    again = client.get(f"/api/v1/cases/{case_id}/graph")
    assert [edge["id"] for edge in again.json()["edges"]] == [edge["id"] for edge in body["edges"]]
    assert client.get(f"/api/v1/cases/{case_id}/graph", params={"max_hops": 6}).status_code == 422
    dated = client.get(
        f"/api/v1/cases/{case_id}/graph",
        params={"booking_date_from": "2026-01-18", "booking_date_to": "2026-01-18"},
    )
    assert dated.status_code == 200
    assert dated.json()["edges"]
    assert all(edge["booking_date"] == "2026-01-18" for edge in dated.json()["edges"])
    other = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-GRAPH-B",
            "title": "Secret other title",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    other_id = other.json()["id"]
    one = next(item for item in intelligence_statements() if item[0] == "100000000011")
    assert (
        client.post(
            f"/api/v1/cases/{other_id}/statements",
            files={"file": (one[1], one[2], "text/csv")},
            data={"subject_account": one[0], "subject_ifsc": IFSC},
        ).status_code
        == 201
    )
    signals = client.get(f"/api/v1/cases/{case_id}/cross-case-signals")
    assert signals.status_code == 200, signals.text
    shared = next(item for item in signals.json()["items"] if item["masked"] == "****0011")
    assert shared["other_case_count"] == 1
    assert "Secret other title" not in signals.text
    outsider = _user(client, "graph-outsider", "investigator")
    assert outsider
    assert client.get(f"/api/v1/cases/{case_id}/graph").status_code == 404
    _login(client, "graph-owner")
    assert client.get(f"/api/v1/cases/{other_id}/graph").status_code == 200
