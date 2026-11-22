"""Investigation workspace reads, evidence, and payment-gateway records."""

import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.application import bridge_service, correlation_service, investigation_service

router = APIRouter(prefix="/api/v1", tags=["investigation"])


class GatewayIn(BaseModel):
    source_record_id: str = Field(min_length=1, max_length=64)
    source_system: str = Field(default="payment_gateway", min_length=1, max_length=64)
    payment_reference: str = Field(min_length=1, max_length=64)
    payer_account: str | None = Field(default=None, max_length=34)
    payer_ifsc: str | None = Field(default=None, max_length=11)
    payee_account: str = Field(min_length=1, max_length=34)
    payee_ifsc: str = Field(min_length=11, max_length=11)
    merchant_domain: str = Field(min_length=1, max_length=253)
    merchant_label: str = Field(default="", max_length=120)
    amount: str = Field(min_length=1, max_length=24)
    currency: str = Field(min_length=3, max_length=3)
    processed_at: str = Field(min_length=10, max_length=40)


@router.get("/cases/{case_id}/summary")
def get_summary(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return investigation_service.summary(db, principal, case_id)


@router.get("/cases/{case_id}/entities")
def get_entities(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return investigation_service.entities(db, principal, case_id)


@router.get("/cases/{case_id}/audit-events")
def get_audit(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return investigation_service.audit_events(db, principal, case_id)


@router.get("/cases/{case_id}/evidence/{object_kind}/{object_id}")
def get_evidence(
    case_id: uuid.UUID,
    object_kind: str,
    object_id: uuid.UUID,
    request: Request,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    return investigation_service.evidence(db, principal, case_id, object_kind, object_id)


@router.get("/relationships/{relationship_id}/evidence")
def get_relationship_evidence(
    relationship_id: uuid.UUID, request: Request, db: Session = DB
) -> dict[str, object]:
    principal = require_principal(request, db)
    return correlation_service.relationship_evidence(db, principal, relationship_id)


@router.get("/cases/{case_id}/gateway-records")
def get_gateway_records(case_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return bridge_service.list_gateway_records(db, principal, case_id)


@router.post("/cases/{case_id}/gateway-records", status_code=201)
def post_gateway_record(
    case_id: uuid.UUID, body: GatewayIn, request: Request, db: Session = DB
) -> dict[str, object]:
    principal = require_principal(request, db)
    row = bridge_service.add_gateway_record(
        db,
        principal,
        case_id=case_id,
        source_record_id=body.source_record_id,
        source_system=body.source_system,
        payment_reference=body.payment_reference,
        payer_account=body.payer_account,
        payer_ifsc=body.payer_ifsc,
        payee_account=body.payee_account,
        payee_ifsc=body.payee_ifsc,
        merchant_domain=body.merchant_domain,
        merchant_label=body.merchant_label,
        amount=body.amount,
        currency=body.currency,
        processed_at=body.processed_at,
        request_id=request_id_of(request),
    )
    return correlation_service.source_record(db, row.case_id, "gateway_record", row.id)
