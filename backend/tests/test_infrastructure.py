"""Infrastructure observations stay historical, and overlap is not ownership."""

import json
import socket

import pytest
from fastapi.testclient import TestClient

from vagexa.api.main import create_app
from vagexa.config import load_settings
from vagexa.intelligence.digital.normalise import (
    OVERLAP_LIMITATION,
    IndicatorRejected,
    normalise_domain,
    normalise_ip,
    refuse_lookup_target,
)
from vagexa.synthetic.infrastructure import ground_truth, shared_ip_records


def test_domain_and_ip_normalisation() -> None:
    assert normalise_domain(" Syn-A.TEST. ") == "syn-a.test"
    assert normalise_domain("bücher.example") == "xn--bcher-kva.example"
    with pytest.raises(IndicatorRejected):
        normalise_domain("syn a.test")
    assert normalise_ip("192.168.001.002") == "192.168.1.2"
    assert normalise_ip("2001:0db8:0000::1") == "2001:db8::1"


def test_lookup_guard_rejects_private_targets_without_a_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network")

    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    for target in ("127.0.0.1", "10.1.1.1", "169.254.169.254", "::1", "http://203.0.113.50/latest"):
        assert refuse_lookup_target(target) is not None
    assert refuse_lookup_target("syn-a.test") is None


def _user(client: TestClient, name: str, role: str) -> None:
    from vagexa.adapters.persistence.session import init_engine, open_session
    from vagexa.application.auth_service import create_user

    init_engine(load_settings())
    db = open_session()
    try:
        create_user(db, username=name, display_name=name, password="correct-horse", role_names=[role])
        db.commit()
    finally:
        db.close()
    login = client.post("/api/v1/auth/login", json={"username": name, "password": "correct-horse"})
    assert login.status_code == 200, login.text
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]


def _case(client: TestClient, reference: str) -> str:
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": reference,
            "title": "Synthetic infrastructure",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def test_shared_ip_is_overlap_and_history_is_kept(client: TestClient) -> None:
    truth = ground_truth()
    _user(client, "infra-owner", "investigator")
    case_id = _case(client, "SYN-INFRA")
    payload = json.dumps({"records": shared_ip_records(), "data_classification": "synthetic"}).encode()
    imported = client.post(
        f"/api/v1/cases/{case_id}/observations/import",
        files={"file": ("observations.json", payload, "application/json")},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["errors"] == []
    listed = client.get(f"/api/v1/cases/{case_id}/observations")
    assert listed.status_code == 200
    names = {row["domain"] for row in listed.json()["dns"]}
    assert set(truth["shared_ip_domains"]) <= names
    conflict = {row["rdata"] for row in listed.json()["dns"] if row["domain"] == "syn-a.test"}
    assert conflict == set(truth["conflicting_answers"])
    changed = [row for row in listed.json()["dns"] if row["domain"] == "syn-e.test"]
    assert {row["rdata"] for row in changed} == set(truth["address_change"])
    assert listed.json()["registration_reason"] == "not_collected"
    graph = client.get(f"/api/v1/cases/{case_id}/graph").json()
    overlaps = [edge for edge in graph["edges"] if edge["kind"] == "infrastructure_overlap"]
    assert overlaps
    assert all(edge["explanation"] == OVERLAP_LIMITATION for edge in overlaps)
    assert all(edge["assertion_kind"] == "verified" for edge in overlaps)
    resolves = [edge for edge in graph["edges"] if edge["kind"] == "resolves_to"]
    assert len(resolves) >= 2
    assert (
        client.post(
            f"/api/v1/cases/{case_id}/observations",
            json={"kind": "certificate", "domain": "syn-a.test", "observed_at": "2026-01-16T09:00:00Z"},
        ).status_code
        == 422
    )
    denied = client.post(
        f"/api/v1/cases/{case_id}/observations/dns",
        json={"domain": "syn-a.test"},
    )
    assert denied.status_code == 409
    _user(client, "infra-outsider", "investigator")
    assert client.get(f"/api/v1/cases/{case_id}/observations").status_code == 404


def test_enabled_lookup_still_refuses_a_link_local_target() -> None:
    settings = load_settings().model_copy(update={"passive_intel": True})
    app = create_app(settings)
    with TestClient(app) as client:
        _user(client, "infra-live", "investigator")
        case_id = _case(client, "SYN-LIVE-DNS")
        refused = client.post(
            f"/api/v1/cases/{case_id}/observations/dns",
            json={"domain": "169.254.169.254"},
        )
        assert refused.status_code == 422
        public = client.post(
            f"/api/v1/cases/{case_id}/observations/dns",
            json={"domain": "syn-a.test"},
        )
        assert public.status_code == 409
        assert "no-resolver" in public.text or "No resolver" in public.text
