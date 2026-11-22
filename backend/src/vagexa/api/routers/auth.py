from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vagexa.api.deps import COOKIE, DB, request_id_of, require_principal
from vagexa.application import auth_service
from vagexa.config import Settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


@router.post("/login")
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: Session = DB,
) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    token, csrf, principal = auth_service.login(
        db,
        username=body.username,
        password=body.password,
        request_id=request_id_of(request),
        user_agent=request.headers.get("user-agent"),
        client_ip=_client_ip(request),
        presented_token=request.cookies.get(COOKIE),
    )
    response.set_cookie(
        key=COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=auth_service.SESSION_HOURS * 3600,
        path="/",
    )
    return {
        "user": {
            "id": str(principal.id),
            "username": principal.username,
            "display_name": principal.display_name,
        },
        "roles": principal.roles,
        "permissions": sorted(principal.permissions),
        "data_mode": settings.data_mode,
        "csrf_token": csrf,
    }


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = DB) -> None:
    require_principal(request, db)
    token = request.cookies.get(COOKIE)
    if token:
        auth_service.logout(db, token, request_id_of(request))
    response.delete_cookie(COOKIE, path="/")


@router.get("/me")
def me(request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    settings: Settings = request.app.state.settings
    csrf = auth_service.issue_csrf(db, principal)
    return {
        "user": {
            "id": str(principal.id),
            "username": principal.username,
            "display_name": principal.display_name,
        },
        "roles": principal.roles,
        "permissions": sorted(principal.permissions),
        "data_mode": settings.data_mode,
        "csrf_token": csrf,
    }


class PasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


@router.post("/password")
def password(
    body: PasswordIn,
    request: Request,
    response: Response,
    db: Session = DB,
) -> dict[str, str]:
    principal = require_principal(request, db)
    settings: Settings = request.app.state.settings
    token, csrf = auth_service.change_password(
        db,
        principal=principal,
        current_password=body.current_password,
        new_password=body.new_password,
        request_id=request_id_of(request),
    )
    response.set_cookie(
        key=COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=auth_service.SESSION_HOURS * 3600,
        path="/",
    )
    return {"status": "changed", "csrf_token": csrf}
