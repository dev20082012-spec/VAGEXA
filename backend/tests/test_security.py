import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings
from vagexa.domain.passwords import hash_password, verify_password


def _user(username: str, password: str, role: str) -> str:
    init_engine(load_settings())
    db = open_session()
    try:
        user = create_user(db, username=username, display_name=username, password=password, role_names=[role])
        db.commit()
        return str(user.id)
    finally:
        db.close()


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["csrf_token"]
    client.headers["X-CSRF-Token"] = token
    return token


def test_password_is_hashed_not_stored_plaintext() -> None:
    stored = hash_password("correct-horse")
    assert stored != "correct-horse"
    assert stored.startswith("$argon2id$")
    assert verify_password(stored, "correct-horse")
    assert not verify_password(stored, "other-secret")


def test_cookie_is_httponly_and_login_does_not_echo_password(client: TestClient) -> None:
    _user("cookie-user", "correct-horse", "investigator")
    response = client.post(
        "/api/v1/auth/login", json={"username": "cookie-user", "password": "correct-horse"}
    )
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "correct-horse" not in cookie
    assert "correct-horse" not in response.text


def test_disabled_account_cannot_sign_in(client: TestClient) -> None:
    user_id = _user("disabled-user", "correct-horse", "investigator")
    _user("admin-sec", "correct-horse", "administrator")
    _login(client, "admin-sec", "correct-horse")
    status = client.post(f"/api/v1/users/{user_id}/status", json={"status": "disabled"})
    assert status.status_code == 200
    client.post("/api/v1/auth/logout")
    denied = client.post(
        "/api/v1/auth/login", json={"username": "disabled-user", "password": "correct-horse"}
    )
    assert denied.status_code == 403


def test_logout_revokes_the_session(client: TestClient) -> None:
    _user("logout-user", "correct-horse", "investigator")
    _login(client, "logout-user", "correct-horse")
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_expired_session_is_rejected(client: TestClient) -> None:
    _user("expire-user", "correct-horse", "investigator")
    _login(client, "expire-user", "correct-horse")
    engine = create_engine(os.environ["VAGEXA_DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(text("UPDATE sessions SET expires_at = now() - interval '1 minute'"))
    engine.dispose()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_replaces_a_presented_session(client: TestClient) -> None:
    _user("fix-user", "correct-horse", "investigator")
    first = client.post("/api/v1/auth/login", json={"username": "fix-user", "password": "correct-horse"})
    old_cookie = client.cookies.get("vagexa_session")
    second = client.post("/api/v1/auth/login", json={"username": "fix-user", "password": "correct-horse"})
    assert client.cookies.get("vagexa_session") != old_cookie
    client.cookies.set("vagexa_session", old_cookie)
    assert client.get("/api/v1/auth/me").status_code == 401
    _ = first
    _ = second


def test_mutating_request_without_csrf_is_rejected(client: TestClient) -> None:
    _user("csrf-user", "correct-horse", "investigator")
    login = client.post("/api/v1/auth/login", json={"username": "csrf-user", "password": "correct-horse"})
    client.headers.pop("X-CSRF-Token", None)
    blocked = client.post(
        "/api/v1/cases",
        json={
            "reference": "CSRF-1",
            "title": "Blocked",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert blocked.status_code == 403
    assert "CSRF-1" not in blocked.text
    _ = login


def test_password_change_revokes_other_sessions(client: TestClient) -> None:
    _user("pw-user", "correct-horse", "investigator")
    client.post("/api/v1/auth/login", json={"username": "pw-user", "password": "correct-horse"})
    first_cookie = client.cookies.get("vagexa_session")
    client.cookies.clear()
    _login(client, "pw-user", "correct-horse")
    changed = client.post(
        "/api/v1/auth/password",
        json={"current_password": "correct-horse", "new_password": "new-secret-1"},
    )
    assert changed.status_code == 200
    client.cookies.set("vagexa_session", first_cookie)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_brute_force_lockout(client: TestClient) -> None:
    _user("lock-user", "correct-horse", "investigator")
    for _ in range(10):
        failed = client.post(
            "/api/v1/auth/login", json={"username": "lock-user", "password": "wrong-password"}
        )
        assert failed.status_code == 401
    locked = client.post("/api/v1/auth/login", json={"username": "lock-user", "password": "correct-horse"})
    assert locked.status_code == 429


def test_analyst_cannot_create_users_or_cases(client: TestClient) -> None:
    _user("analyst-sec", "correct-horse", "analyst")
    _login(client, "analyst-sec", "correct-horse")
    users = client.post(
        "/api/v1/users",
        json={
            "username": "new-person",
            "display_name": "New",
            "password": "correct-horse",
            "roles": ["investigator"],
        },
    )
    assert users.status_code == 403
    cases = client.post(
        "/api/v1/cases",
        json={
            "reference": "NOPE",
            "title": "Hidden",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    assert cases.status_code == 403


def test_cross_case_access_is_denied_without_the_title(client: TestClient) -> None:
    _user("owner-a", "correct-horse", "investigator")
    _user("owner-b", "correct-horse", "investigator")
    _login(client, "owner-a", "correct-horse")
    created = client.post(
        "/api/v1/cases",
        json={
            "reference": "SYN-OWN",
            "title": "Private title",
            "opened_on": "2026-01-15",
            "data_classification": "synthetic",
        },
    )
    case_id = created.json()["id"]
    client.post("/api/v1/auth/logout")
    _login(client, "owner-b", "correct-horse")
    denied = client.get(f"/api/v1/cases/{case_id}")
    assert denied.status_code == 404
    assert "Private title" not in denied.text


def test_login_failure_audit_does_not_store_the_password(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    client.post("/api/v1/auth/login", json={"username": "nobody", "password": "super-secret-value"})
    captured = capsys.readouterr()
    assert "super-secret-value" not in captured.out
    assert "super-secret-value" not in captured.err
