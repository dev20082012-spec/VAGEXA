"""Payment-gateway records: a third-party row naming a reference, accounts, and a merchant domain."""

import uuid
from datetime import UTC, datetime
from decimal import InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import (
    Case,
    CaseAssignment,
    DomainName,
    GatewayRecord,
    ProvenanceRecord,
)
from vagexa.api.errors import Problem
from vagexa.application.auth_service import Principal
from vagexa.application.correlation_service import source_record
from vagexa.application.ingestion_service import resolve_account
from vagexa.domain.authorization import case_role_allows
from vagexa.intelligence.digital.normalise import IndicatorRejected, normalise_domain
from vagexa.intelligence.financial.canonical import (
    normalise_account,
    normalise_ifsc,
    parse_amount,
)

GATEWAY_METHOD = "gateway_record.v1"


def _case(db: Session, principal: Principal, case_id: uuid.UUID, *, write: bool) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None or not case_role_allows(assignment.case_role, "cases.read"):
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    if write and not case_role_allows(assignment.case_role, "cases.mutate"):
        raise Problem(403, "forbidden", "Not allowed", "You cannot add source records to this case.")
    return case


def add_gateway_record(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    source_record_id: str,
    source_system: str,
    payment_reference: str,
    payer_account: str | None,
    payer_ifsc: str | None,
    payee_account: str,
    payee_ifsc: str,
    merchant_domain: str,
    merchant_label: str,
    amount: str,
    currency: str,
    processed_at: str,
    request_id: str | None,
) -> GatewayRecord:
    case = _case(db, principal, case_id, write=True)
    record_id = source_record_id.strip()
    if not record_id or len(record_id) > 64:
        raise Problem(422, "invalid", "Invalid record id", "The source record id must be 1 to 64 characters.")
    existing = db.scalar(
        select(GatewayRecord).where(
            GatewayRecord.case_id == case.id, GatewayRecord.source_record_id == record_id
        )
    )
    if existing is not None:
        return existing
    reference = payment_reference.strip()
    if not reference:
        raise Problem(422, "invalid", "Missing reference", "A gateway record needs a payment reference.")
    try:
        domain_name = normalise_domain(merchant_domain)
    except IndicatorRejected as exc:
        raise Problem(422, exc.code, "Invalid domain", exc.message) from exc
    try:
        value = parse_amount(amount)
    except InvalidOperation as exc:
        raise Problem(
            422, "invalid_amount", "Invalid amount", "Use a positive decimal with at most four places."
        ) from exc
    code = currency.strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise Problem(422, "invalid_currency", "Invalid currency", "Use a three-letter currency code.")
    try:
        when = datetime.fromisoformat(processed_at.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise Problem(422, "invalid_time", "Invalid time", "processed_at must be an ISO timestamp.") from exc
    if when.tzinfo is None:
        raise Problem(422, "invalid_time", "Invalid time", "processed_at needs a time zone.")
    payee_number = normalise_account(payee_account)
    payee_code = normalise_ifsc(payee_ifsc)
    if not payee_number or not payee_code:
        raise Problem(422, "missing_field", "Missing payee", "The payee account and IFSC are required.")
    payee = resolve_account(db, payee_number, payee_code, None)
    payer = None
    payer_number = normalise_account(payer_account)
    if payer_number:
        payer_code = normalise_ifsc(payer_ifsc)
        if not payer_code:
            raise Problem(422, "missing_field", "Missing payer IFSC", "A payer account needs an IFSC.")
        payer = resolve_account(db, payer_number, payer_code, None)
    domain = db.scalar(select(DomainName).where(DomainName.name_norm == domain_name))
    if domain is None:
        domain = DomainName(name_norm=domain_name)
        db.add(domain)
        db.flush()
    provenance = ProvenanceRecord(
        data_classification=case.data_classification,
        source_system=source_system.strip() or "payment_gateway",
        source_reference=record_id,
        collected_at=datetime.now(UTC),
        collected_by=str(principal.id),
        method_name=GATEWAY_METHOD,
        raw_hash=None,
    )
    db.add(provenance)
    db.flush()
    row = GatewayRecord(
        case_id=case.id,
        source_record_id=record_id,
        source_system=provenance.source_system,
        payment_reference=reference,
        payer_account_id=payer.id if payer else None,
        payee_account_id=payee.id,
        merchant_domain_id=domain.id,
        merchant_label=merchant_label.strip() or domain_name,
        amount=value,
        currency=code,
        processed_at=when.astimezone(UTC),
        original_record={
            "source_record_id": record_id,
            "payment_reference": reference,
            "payer_account": payer_account or "",
            "payee_account": payee_account,
            "merchant_domain": merchant_domain,
            "merchant_label": merchant_label,
            "amount": amount,
            "currency": currency,
            "processed_at": processed_at,
        },
        data_classification=case.data_classification,
        provenance_id=provenance.id,
    )
    db.add(row)
    db.flush()
    append_audit(
        db,
        action="gateway_record.add",
        outcome="success",
        object_kind="gateway_record",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(row.id),
        request_id=request_id,
        detail={"source_system": row.source_system},
    )
    return row


def list_gateway_records(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    case = _case(db, principal, case_id, write=False)
    rows = list(
        db.scalars(
            select(GatewayRecord)
            .where(GatewayRecord.case_id == case.id)
            .order_by(GatewayRecord.processed_at, GatewayRecord.id)
            .limit(200)
        )
    )
    return {"items": [source_record(db, case.id, "gateway_record", row.id) for row in rows]}
