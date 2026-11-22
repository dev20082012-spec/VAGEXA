from pathlib import Path

from fastapi.testclient import TestClient

from vagexa.api.main import create_app
from vagexa.config import load_settings
from vagexa.deploy_boot import main


def test_production_hides_api_docs() -> None:
    settings = load_settings().model_copy(update={"environment": "production"})
    with TestClient(create_app(settings)) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/health/live").status_code == 200


def test_ready_stays_down_until_the_demonstration_case_exists() -> None:
    settings = load_settings().model_copy(update={"require_demo": True})
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["reason"] == "demonstration-case"
        assert "password" not in response.text.lower()


def test_static_routes_serve_the_app_and_leave_the_api_in_place(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<!doctype html><title>VAGEXA</title>", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('app')", encoding="utf-8")
    settings = load_settings().model_copy(update={"static_dir": str(tmp_path)})
    with TestClient(create_app(settings)) as client:
        assert "VAGEXA" in client.get("/").text
        assert "VAGEXA" in client.get("/cases/11111111-1111-1111-1111-111111111111/report").text
        script = client.get("/assets/app.js")
        assert script.status_code == 200
        assert "console.log" in script.text
        assert client.get("/health/live").status_code == 200
        outside = client.get("/../pyproject.toml")
        assert "VAGEXA" in outside.text or outside.status_code == 404


def test_boot_refuses_to_start_without_a_password(monkeypatch) -> None:
    monkeypatch.delenv("VAGEXA_BOOTSTRAP_USERNAME", raising=False)
    monkeypatch.delenv("VAGEXA_BOOTSTRAP_PASSWORD", raising=False)
    try:
        main()
    except SystemExit as exc:
        assert "PASSWORD" in str(exc)
    else:
        raise AssertionError("boot continued without a password")
