"""The database dependency must commit before the response is sent."""

from pathlib import Path

from vagexa.api.deps import DB

ROUTERS = Path(__file__).resolve().parents[1] / "src" / "vagexa" / "api" / "routers"


def test_db_dependency_ends_before_the_response() -> None:
    assert DB.scope == "function"


def test_no_router_uses_the_request_scoped_session() -> None:
    offenders = [path.name for path in ROUTERS.glob("*.py") if "Depends(get_db)" in path.read_text("utf-8")]
    assert offenders == []
