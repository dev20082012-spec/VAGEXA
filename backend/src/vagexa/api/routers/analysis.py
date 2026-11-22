"""Financial analysis routes. Allocation stays in the domain modules."""

import uuid
from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.application import analysis_service

router = APIRouter(prefix="/api/v1", tags=["analysis"])


class TraceIn(BaseModel):
    seed_transaction_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    policy: str = "fifo"
    policy_version: str = "fifo.v1"
    max_layer: int = Field(default=3, ge=1, le=5)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class IndicatorIn(BaseModel):
    window_start: date
    window_end: date
    fan_in_min: int = Field(default=3, ge=1, le=1000)
    fan_out_min: int = Field(default=3, ge=1, le=1000)
    pass_through_ratio: str = "0.85"
    pass_through_dwell_hours: str = "24"
    amount_floor: str = "1000.0000"
    currency: str = Field(default="INR", min_length=3, max_length=3)


class WalkIn(BaseModel):
    start_account_id: uuid.UUID
    direction: str
    max_layer: int = Field(default=3, ge=1, le=5)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    window_start: date
    window_end: date
    amount_min: str | None = None
    amount_max: str | None = None


def _currency(value: str) -> str:
    return value.strip().upper()


@router.post("/cases/{case_id}/traces")
def post_trace(case_id: uuid.UUID, body: TraceIn, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    if body.policy != "fifo" or body.policy_version != "fifo.v1":
        from vagexa.api.errors import Problem

        raise Problem(422, "invalid", "Unsupported policy", "Phase 1 allocation is fifo.v1.")
    return analysis_service.run_trace(
        db,
        principal,
        case_id=case_id,
        seed_transaction_ids=body.seed_transaction_ids,
        max_layer=body.max_layer,
        currency=_currency(body.currency),
        request_id=request_id_of(request),
    )


@router.get("/traces/{trace_id}")
def get_trace(trace_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.get_trace(db, principal, trace_id)


@router.post("/cases/{case_id}/indicator-runs")
def post_indicators(
    case_id: uuid.UUID, body: IndicatorIn, request: Request, db: Session = DB
) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.run_indicators(
        db,
        principal,
        case_id=case_id,
        window_start=body.window_start,
        window_end=body.window_end,
        fan_in_min=body.fan_in_min,
        fan_out_min=body.fan_out_min,
        pass_through_ratio=analysis_service.parse_amount(body.pass_through_ratio),
        pass_through_dwell_hours=analysis_service.parse_amount(body.pass_through_dwell_hours),
        amount_floor=analysis_service.parse_amount(body.amount_floor),
        currency=_currency(body.currency),
        request_id=request_id_of(request),
    )


@router.get("/cases/{case_id}/indicators")
def get_indicators(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.list_indicators(db, principal, case_id)


@router.post("/cases/{case_id}/statement-walks")
def post_walk(case_id: uuid.UUID, body: WalkIn, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.run_walk(
        db,
        principal,
        case_id=case_id,
        start_account_id=body.start_account_id,
        direction=body.direction,
        max_layer=body.max_layer,
        currency=_currency(body.currency),
        window_start=body.window_start,
        window_end=body.window_end,
        amount_min=body.amount_min,
        amount_max=body.amount_max,
        request_id=request_id_of(request),
    )


@router.get("/statement-walks/{walk_id}")
def get_walk(walk_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.get_walk(db, principal, walk_id)


@router.get("/cases/{case_id}/findings")
def get_findings(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.list_findings(db, principal, case_id)


@router.get("/findings/{finding_id}")
def get_finding(finding_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.get_finding(db, principal, finding_id)


@router.get("/cases/{case_id}/analytical-runs")
def get_runs(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.list_runs(db, principal, case_id)


@router.get("/cases/{case_id}/activity")
def get_activity(
    case_id: uuid.UUID,
    request: Request,
    currency: str | None = None,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.activity(db, principal, case_id, currency)


@router.get("/cases/{case_id}/financial-summary")
def get_summary(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return analysis_service.overview(db, principal, case_id)
