import pytest
from pydantic import ValidationError

from vagexa.config import Settings
from vagexa.domain.classification import ClassificationRejected, assert_case_classification


def test_settings_require_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VAGEXA_DATABASE_URL", raising=False)
    monkeypatch.setenv("VAGEXA_DATA_MODE", "synthetic")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_insecure_cookie_refused_in_operational_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            data_mode="operational",
            database_url="postgresql+psycopg://vagexa@127.0.0.1/vagexa",
            cookie_secure=False,
        )


def test_synthetic_mode_refuses_official_cases() -> None:
    with pytest.raises(ClassificationRejected):
        assert_case_classification("synthetic", "official")


def test_operational_mode_refuses_synthetic_cases() -> None:
    with pytest.raises(ClassificationRejected):
        assert_case_classification("operational", "synthetic")
