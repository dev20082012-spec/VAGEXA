import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.api.errors import Problem
from vagexa.application import auth_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    roles: list[str] = Field(min_length=1)


@router.post("", status_code=201)
def post_user(body: UserIn, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    if "users.manage" not in principal.permissions:
        raise Problem(403, "forbidden", "Not allowed", "You cannot create users.")
    user = auth_service.create_user(
        db,
        username=body.username,
        display_name=body.display_name,
        password=body.password,
        role_names=body.roles,
    )
    append_audit(
        db,
        action="user.create",
        outcome="success",
        object_kind="user",
        actor_id=principal.id,
        object_id=str(user.id),
        request_id=request_id_of(request),
    )
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "status": user.status,
        "roles": body.roles,
    }


class StatusIn(BaseModel):
    status: str = Field(pattern=r"^(active|disabled)$")


@router.post("/{user_id}/status")
def post_status(
    user_id: uuid.UUID,
    body: StatusIn,
    request: Request,
    db: Session = DB,
) -> dict[str, str]:
    principal = require_principal(request, db)
    auth_service.set_account_status(
        db,
        actor=principal,
        user_id=user_id,
        status=body.status,
        request_id=request_id_of(request),
    )
    return {"status": body.status}
