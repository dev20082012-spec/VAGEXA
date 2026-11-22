from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.session import session_scope
from vagexa.api.errors import Problem
from vagexa.application.auth_service import Principal, principal_from_token

COOKIE = "vagexa_session"


def get_db() -> Iterator[Session]:
    yield from session_scope()


# The commit must finish before the response is sent. With the default request scope the
# client can send its next call, for example GET /me after login, before the session row exists.
DB = Depends(get_db, scope="function")


def request_id_of(request: Request) -> str:
    return str(getattr(request.state, "request_id", ""))


def require_principal(request: Request, db: Session) -> Principal:
    token = request.cookies.get(COOKIE)
    if not token:
        raise Problem(401, "unauthenticated", "Sign-in required", "Sign in to continue.")
    principal = principal_from_token(db, token)
    if principal is None:
        raise Problem(401, "unauthenticated", "Sign-in required", "Sign in to continue.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        from vagexa.application.auth_service import csrf_matches

        if not csrf_matches(db, token, request.headers.get("x-csrf-token")):
            raise Problem(403, "forbidden", "Request blocked", "The request could not be verified.")
    return principal
