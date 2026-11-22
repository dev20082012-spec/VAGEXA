"""Correlation proposals and investigator decisions."""

import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.application import correlation_service

router = APIRouter(prefix="/api/v1", tags=["correlation"])


class ReviewIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


@router.post("/cases/{case_id}/correlations")
def post_correlation(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return correlation_service.run_correlation(db, principal, case_id, request_id_of(request))


@router.get("/cases/{case_id}/relationships")
def get_relationships(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return correlation_service.list_relationships(db, principal, case_id)


@router.get("/relationships/{relationship_id}")
def get_relationship(relationship_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return correlation_service.get_relationship(db, principal, relationship_id)


@router.post("/relationships/{relationship_id}/confirm")
def confirm(
    relationship_id: uuid.UUID,
    request: Request,
    body: ReviewIn | None = None,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    note = body.note if body else None
    return correlation_service.decide(
        db, principal, relationship_id, "confirmed", note or "", request_id_of(request)
    )


@router.post("/relationships/{relationship_id}/reject")
def reject(
    relationship_id: uuid.UUID,
    request: Request,
    body: ReviewIn | None = None,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    note = body.note if body else None
    return correlation_service.decide(
        db, principal, relationship_id, "rejected", note or "", request_id_of(request)
    )
