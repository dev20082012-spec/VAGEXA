from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from vagexa import __version__
from vagexa.adapters.persistence.models import Case
from vagexa.adapters.persistence.session import check_database, open_session
from vagexa.config import Settings
from vagexa.synthetic.demo import REFERENCE

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "live", "version": __version__}


def _demonstration_case_present() -> bool:
    db = open_session()
    try:
        found = db.scalar(select(Case.id).where(Case.reference == REFERENCE))
        return found is not None
    finally:
        db.close()


@router.get("/health/ready")
def ready(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    try:
        check_database()
        if settings.require_demo and not _demonstration_case_present():
            return JSONResponse(
                status_code=503,
                content={"status": "not-ready", "version": __version__, "reason": "demonstration-case"},
            )
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not-ready", "version": __version__})
    body = {"status": "ready", "version": __version__}
    if settings.require_demo:
        body["demonstration_case"] = REFERENCE
    return JSONResponse(status_code=200, content=body)
