"""Infrastructure observations. The handler does not resolve names."""

import uuid
from datetime import datetime

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.application import infrastructure_service
from vagexa.config import Settings

router = APIRouter(prefix="/api/v1", tags=["infrastructure"])


class ObservationIn(BaseModel):
    kind: str
    domain: str | None = None
    rrtype: str | None = None
    rdata: str | None = None
    ip: str | None = None
    provider_name: str | None = None
    source_note: str | None = Field(default=None, max_length=2000)
    note: str | None = None
    observed_at: datetime


class LookupIn(BaseModel):
    domain: str = Field(min_length=1, max_length=253)


@router.post("/cases/{case_id}/observations", status_code=201)
def post_observation(
    case_id: uuid.UUID,
    body: ObservationIn,
    request: Request,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    if body.kind == "hosting":
        hosting = infrastructure_service.add_hosting(
            db,
            principal,
            case_id=case_id,
            ip=body.ip or body.rdata,
            provider_name=body.provider_name,
            source_note=body.source_note or body.note or "",
            observed_at=body.observed_at.isoformat(),
            request_id=request_id_of(request),
        )
        return {"id": str(hosting.id), "kind": "hosting"}
    if body.kind != "dns":
        from vagexa.api.errors import Problem

        raise Problem(
            422,
            "unsupported_kind",
            "Unsupported indicator",
            "This release stores dns and hosting observations. Certificates and RDAP are not collected.",
        )
    dns = infrastructure_service.add_dns(
        db,
        principal,
        case_id=case_id,
        domain=body.domain or "",
        rrtype=body.rrtype or "",
        rdata=body.rdata or "",
        observed_at=body.observed_at.isoformat(),
        request_id=request_id_of(request),
    )
    return {"id": str(dns.id), "kind": "dns", "rrtype": dns.rrtype}


@router.post("/cases/{case_id}/observations/import", status_code=201)
async def post_import(
    case_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    settings: Settings = request.app.state.settings
    payload = await file.read(1_000_001)
    if len(payload) > settings.upload_max_bytes:
        from vagexa.api.errors import Problem

        raise Problem(413, "payload-too-large", "File too large", "The upload exceeds the size limit.")
    return infrastructure_service.import_observations(
        db,
        principal,
        case_id=case_id,
        filename=file.filename or "observations.json",
        payload=payload,
        request_id=request_id_of(request),
    )


@router.get("/cases/{case_id}/observations")
def get_observations(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return infrastructure_service.list_observations(db, principal, case_id)


@router.post("/cases/{case_id}/observations/dns", status_code=409)
def post_lookup(
    case_id: uuid.UUID,
    body: LookupIn,
    request: Request,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    infrastructure_service._case(db, principal, case_id, write=True, request_id=request_id_of(request))
    infrastructure_service.request_passive_lookup(request.app.state.settings, body.domain)
    return {}
