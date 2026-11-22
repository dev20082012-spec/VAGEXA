"""Case graph. The response is computed and not stored."""

import uuid
from datetime import date

from fastapi import APIRouter, Query, Request
from sqlalchemy.orm import Session

from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.application import graph_service

router = APIRouter(prefix="/api/v1", tags=["graph"])


@router.get("/cases/{case_id}/graph")
def get_graph(
    case_id: uuid.UUID,
    request: Request,
    focus: uuid.UUID | None = None,
    max_hops: int = Query(default=3, ge=1, le=5),
    trace_id: uuid.UUID | None = None,
    path_from: uuid.UUID | None = None,
    path_to: uuid.UUID | None = None,
    booking_date_from: date | None = None,
    booking_date_to: date | None = None,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    return graph_service.case_graph(
        db,
        principal,
        case_id=case_id,
        focus=focus,
        max_hops=max_hops,
        trace_id=trace_id,
        path_from=path_from,
        path_to=path_to,
        booking_date_from=booking_date_from,
        booking_date_to=booking_date_to,
        request_id=request_id_of(request),
    )


@router.get("/cases/{case_id}/cross-case-signals")
def get_signals(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return graph_service.cross_case_signals(db, principal, case_id, request_id_of(request))
