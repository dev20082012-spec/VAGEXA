import uuid
from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.models import Case
from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.application import case_service
from vagexa.config import Settings

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


class CaseIn(BaseModel):
    reference: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    opened_on: date
    data_classification: str
    synthetic_batch_id: uuid.UUID | None = None


def _case_body(case: Case) -> dict[str, object]:
    return {
        "id": str(case.id),
        "reference": case.reference,
        "title": case.title,
        "status": case.status,
        "data_classification": case.data_classification,
        "opened_on": case.opened_on.isoformat(),
        "synthetic_batch_id": str(case.synthetic_batch_id) if case.synthetic_batch_id else None,
    }


@router.get("")
def list_cases(request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    items = [_case_body(case) for case in case_service.list_cases(db, principal)]
    return {"items": items, "next_cursor": None}


@router.post("", status_code=201)
def post_case(body: CaseIn, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    settings: Settings = request.app.state.settings
    case = case_service.create_case(
        db,
        principal,
        reference=body.reference,
        title=body.title,
        opened_on=body.opened_on,
        data_classification=body.data_classification,
        data_mode=settings.data_mode,
        synthetic_batch_id=body.synthetic_batch_id,
        request_id=request_id_of(request),
    )
    payload = _case_body(case)
    payload["counts"] = {"statements": 0, "transactions": 0, "proposed_relationships": 0}
    return payload


class AssignmentIn(BaseModel):
    user_id: uuid.UUID
    case_role: str


@router.post("/{case_id}/assignments", status_code=201)
def post_assignment(
    case_id: uuid.UUID,
    body: AssignmentIn,
    request: Request,
    db: Session = DB,
) -> dict[str, str]:
    principal = require_principal(request, db)
    case_service.assign_case(
        db,
        principal,
        case_id=case_id,
        user_id=body.user_id,
        case_role=body.case_role,
        request_id=request_id_of(request),
    )
    return {"status": "assigned"}


@router.get("/{case_id}")
def get_case(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    case = case_service.get_case(db, principal, case_id, request_id_of(request))
    payload = _case_body(case)
    payload["counts"] = {"statements": 0, "transactions": 0, "proposed_relationships": 0}
    return payload
