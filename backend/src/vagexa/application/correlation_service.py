"""Persist correlate proposals. Source rows are not updated."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import (
    Account,
    AnalyticalRun,
    Case,
    CaseAssignment,
    DnsObservation,
    DomainName,
    EvidenceRecord,
    Finding,
    FindingSupport,
    GatewayRecord,
    HostingObservation,
    IpAddress,
    ProvenanceRecord,
    Relationship,
    RelationshipReview,
    RelationshipSupport,
    Statement,
    Transaction,
)
from vagexa.api.errors import Problem
from vagexa.application.auth_service import Principal
from vagexa.domain.authorization import case_role_allows
from vagexa.intelligence.correlation.classify import Classified, RelView, classify
from vagexa.intelligence.correlation.correlate import (
    METHOD_VERSION,
    CorrDns,
    CorrDomain,
    CorrGateway,
    CorrHost,
    CorrIp,
    CorrTx,
    correlate,
)

FOUR = Decimal("0.0001")


def _money(value: object) -> str:
    return f"{Decimal(str(value)).quantize(FOUR):.4f}"


def _mutate(db: Session, principal: Principal, case_id: uuid.UUID, request_id: str | None) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None:
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    if not case_role_allows(assignment.case_role, "cases.mutate"):
        append_audit(
            db,
            action="relationship.decide",
            outcome="denied",
            object_kind="case",
            actor_id=principal.id,
            case_id=case.id,
            object_id=str(case_id),
            request_id=request_id,
        )
        raise Problem(403, "forbidden", "Not allowed", "You cannot change relationships on this case.")
    return case


def _readable(db: Session, principal: Principal, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None or not case_role_allows(assignment.case_role, "cases.read"):
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    return case


def _evidence(
    db: Session, case_id: uuid.UUID, kind: str, object_id: uuid.UUID, provenance_id: uuid.UUID
) -> EvidenceRecord:
    found = db.scalar(
        select(EvidenceRecord).where(
            EvidenceRecord.case_id == case_id,
            EvidenceRecord.kind == kind,
            EvidenceRecord.object_id == object_id,
        )
    )
    if found is not None:
        return found
    digest = hashlib.sha256(f"{kind}|{object_id}".encode()).hexdigest()
    row = EvidenceRecord(
        case_id=case_id,
        provenance_id=provenance_id,
        kind=kind,
        object_id=object_id,
        content_hash=digest,
    )
    db.add(row)
    db.flush()
    return row


def _correlation_bundle(
    db: Session, case_id: uuid.UUID
) -> tuple[
    list[tuple[Transaction, uuid.UUID]],
    list[tuple[DnsObservation, DomainName, IpAddress]],
    list[HostingObservation],
    list[IpAddress],
    list[GatewayRecord],
    str,
]:
    """The rows correlate.v2 reads, plus the hash of their ids. The hash does not include results."""
    superseded = select(Statement.supersedes_statement_id).where(
        Statement.supersedes_statement_id.is_not(None)
    )
    tx_rows = [
        (tx, account_id)
        for tx, account_id in db.execute(
            select(Transaction, Statement.account_id)
            .join(Statement, Statement.id == Transaction.statement_id)
            .where(Transaction.case_id == case_id, Statement.id.not_in(superseded))
        ).all()
    ]
    dns_rows = [
        (obs, domain, ip)
        for obs, domain, ip in db.execute(
            select(DnsObservation, DomainName, IpAddress)
            .join(DomainName, DomainName.id == DnsObservation.domain_id)
            .join(IpAddress, IpAddress.id == DnsObservation.ip_address_id)
            .where(DnsObservation.case_id == case_id)
        ).all()
    ]
    host_rows = list(db.scalars(select(HostingObservation).where(HostingObservation.case_id == case_id)))
    ip_ids = {ip.id for _obs, _domain, ip in dns_rows}
    ip_ids |= {row.ip_address_id for row in host_rows if row.ip_address_id is not None}
    ip_rows = list(db.scalars(select(IpAddress).where(IpAddress.id.in_(ip_ids)))) if ip_ids else []
    gateway_rows = list(db.scalars(select(GatewayRecord).where(GatewayRecord.case_id == case_id)))
    snapshot = {
        "transactions": sorted(str(tx.id) for tx, _account in tx_rows),
        "dns": sorted(str(obs.id) for obs, _domain, _ip in dns_rows),
        "hosting": sorted(str(row.id) for row in host_rows),
        "gateway": sorted(str(row.id) for row in gateway_rows),
    }
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return tx_rows, dns_rows, host_rows, ip_rows, gateway_rows, digest


def correlation_input_hash(db: Session, case_id: uuid.UUID) -> str:
    """Hash of the stored ids a correlation run would read. It is not a score."""
    return _correlation_bundle(db, case_id)[5]


def run_correlation(
    db: Session, principal: Principal, case_id: uuid.UUID, request_id: str | None
) -> dict[str, object]:
    case = _readable(db, principal, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if assignment is None or not case_role_allows(assignment.case_role, "analysis.run"):
        raise Problem(403, "forbidden", "Not allowed", "You cannot run correlation on this case.")
    tx_rows, dns_rows, host_rows, ip_rows, gateway_rows, input_hash = _correlation_bundle(db, case.id)
    proposals, truncated = correlate(
        [
            CorrTx(
                str(tx.id),
                str(account_id),
                tx.narration_raw,
                tx.reference_raw,
                tx.counterparty_resolution,
                direction=tx.direction,
                amount=_money(tx.amount),
                currency=str(tx.currency).strip(),
                counterparty_account_id=str(tx.counterparty_account_id)
                if tx.counterparty_account_id
                else None,
            )
            for tx, account_id in tx_rows
        ],
        [CorrDomain(str(domain.id), domain.name_norm) for _obs, domain, _ip in dns_rows],
        [CorrIp(str(row.id), str(row.address)) for row in ip_rows],
        [CorrDns(str(obs.id), str(domain.id), str(ip.id)) for obs, domain, ip in dns_rows],
        [
            CorrHost(str(row.id), str(row.ip_address_id) if row.ip_address_id else None, row.provider_name)
            for row in host_rows
        ],
        [
            CorrGateway(
                id=str(row.id),
                payment_reference=row.payment_reference,
                payer_account_id=str(row.payer_account_id) if row.payer_account_id else None,
                payee_account_id=str(row.payee_account_id),
                domain_id=str(row.merchant_domain_id),
                amount=_money(row.amount),
                currency=str(row.currency).strip(),
            )
            for row in gateway_rows
        ],
    )
    existing = set(db.scalars(select(Relationship.pair_key).where(Relationship.case_id == case.id)).all())
    fresh = [item for item in proposals if item.pair_key not in existing]
    output_hash = hashlib.sha256(
        json.dumps([item.pair_key for item in proposals], sort_keys=True).encode()
    ).hexdigest()
    run = AnalyticalRun(
        case_id=case.id,
        run_kind="correlation",
        method_name="correlate",
        method_version=METHOD_VERSION,
        parameters={"truncated": truncated, "proposal_count": len(proposals)},
        input_hash=input_hash,
        output_hash=output_hash,
        status="succeeded",
        requested_by=principal.id,
    )
    db.add(run)
    db.flush()
    tx_by_id = {tx.id: tx for tx, _account in tx_rows}
    dns_by_id = {obs.id: obs for obs, _domain, _ip in dns_rows}
    host_by_id = {row.id: row for row in host_rows}
    gateway_by_id = {row.id: row for row in gateway_rows}
    for item in fresh:
        provenance = ProvenanceRecord(
            data_classification=case.data_classification,
            source_system="method",
            source_reference=item.pair_key[:240],
            collected_at=datetime.now(UTC),
            collected_by=str(principal.id),
            method_name=METHOD_VERSION,
            raw_hash=None,
        )
        db.add(provenance)
        db.flush()
        relationship = Relationship(
            case_id=case.id,
            analytical_run_id=run.id,
            pair_key=item.pair_key,
            from_kind=item.from_kind,
            from_id=uuid.UUID(item.from_id),
            to_kind=item.to_kind,
            to_id=uuid.UUID(item.to_id),
            rel_type=item.rel_type,
            assertion_kind=item.assertion_kind,
            method_name="correlate",
            method_version=METHOD_VERSION,
            status="proposed",
            limitation=item.limitation,
            explanation=item.explanation,
            provenance_id=provenance.id,
            created_by=principal.id,
        )
        db.add(relationship)
        db.flush()
        evidence_rows: list[EvidenceRecord] = []
        for object_kind, object_id in item.support:
            parsed = uuid.UUID(object_id)
            db.add(
                RelationshipSupport(
                    relationship_id=relationship.id, object_kind=object_kind, object_id=parsed
                )
            )
            if object_kind == "transaction" and parsed in tx_by_id:
                evidence_rows.append(
                    _evidence(db, case.id, "transaction", parsed, tx_by_id[parsed].provenance_id)
                )
            elif object_kind == "dns_observation" and parsed in dns_by_id:
                evidence_rows.append(
                    _evidence(db, case.id, "observation", parsed, dns_by_id[parsed].provenance_id)
                )
            elif object_kind == "hosting_observation" and parsed in host_by_id:
                evidence_rows.append(
                    _evidence(db, case.id, "observation", parsed, host_by_id[parsed].provenance_id)
                )
            elif object_kind == "gateway_record" and parsed in gateway_by_id:
                evidence_rows.append(
                    _evidence(db, case.id, "observation", parsed, gateway_by_id[parsed].provenance_id)
                )
        if evidence_rows:
            finding = Finding(
                analytical_run_id=run.id,
                case_id=case.id,
                finding_kind="correlation",
                summary=item.explanation,
                assertion_kind=item.assertion_kind,
                limitations=item.limitation,
                method_name="correlate",
                method_version=METHOD_VERSION,
            )
            db.add(finding)
            db.flush()
            seen_evidence: set[uuid.UUID] = set()
            for evidence in evidence_rows:
                if evidence.id in seen_evidence:
                    continue
                seen_evidence.add(evidence.id)
                db.add(FindingSupport(finding_id=finding.id, evidence_id=evidence.id))
    append_audit(
        db,
        action="correlation.run",
        outcome="success",
        object_kind="analytical_run",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(run.id),
        request_id=request_id,
        detail={"inserted": len(fresh), "truncated": truncated, "method_version": METHOD_VERSION},
    )
    return {
        "id": str(run.id),
        "status": "succeeded",
        "method_version": METHOD_VERSION,
        "inserted": len(fresh),
        "already_present": len(proposals) - len(fresh),
        "truncated": truncated,
        "items": list_relationships(db, principal, case.id)["items"],
    }


def list_relationships(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    _readable(db, principal, case_id)
    rows = list(
        db.scalars(
            select(Relationship).where(Relationship.case_id == case_id).order_by(Relationship.created_at)
        )
    )
    classes = classifications(db, case_id)
    return {"items": [_body(db, row, classes) for row in rows]}


def get_relationship(db: Session, principal: Principal, relationship_id: uuid.UUID) -> dict[str, object]:
    row = db.get(Relationship, relationship_id)
    if row is None:
        raise Problem(404, "not-found", "Not available", "This relationship is not available.")
    _readable(db, principal, row.case_id)
    return _body(db, row, classifications(db, row.case_id))


def relationship_evidence(db: Session, principal: Principal, relationship_id: uuid.UUID) -> dict[str, object]:
    row = db.get(Relationship, relationship_id)
    if row is None:
        raise Problem(404, "not-found", "Not available", "This relationship is not available.")
    _readable(db, principal, row.case_id)
    support = list(
        db.scalars(select(RelationshipSupport).where(RelationshipSupport.relationship_id == row.id))
    )
    return {
        "relationship_id": str(row.id),
        "analytical_note": "The relationship is analytical. These items are the stored source records.",
        "items": [source_record(db, row.case_id, item.object_kind, item.object_id) for item in support],
    }


def classifications(db: Session, case_id: uuid.UUID) -> dict[str, Classified]:
    rows = list(db.scalars(select(Relationship).where(Relationship.case_id == case_id)))
    if not rows:
        return {}
    supports = list(
        db.scalars(
            select(RelationshipSupport).where(
                RelationshipSupport.relationship_id.in_([row.id for row in rows])
            )
        )
    )
    by_rel: dict[uuid.UUID, set[str]] = {}
    for item in supports:
        if item.object_kind == "transaction":
            by_rel.setdefault(item.relationship_id, set()).add(str(item.object_id))
    return classify(
        [
            RelView(
                id=str(row.id),
                rel_type=row.rel_type,
                assertion_kind=row.assertion_kind,
                to_id=str(row.to_id),
                transaction_ids=frozenset(by_rel.get(row.id, set())),
            )
            for row in rows
        ]
    )


def _mask(account: Account | None) -> str | None:
    if account is None:
        return None
    key = account.account_number_norm or account.vpa_norm or ""
    return f"****{key[-4:]}" if key else None


def endpoint_label(db: Session, kind: str, identifier: uuid.UUID) -> str | None:
    if kind == "account":
        return _mask(db.get(Account, identifier))
    if kind == "domain":
        domain = db.get(DomainName, identifier)
        return domain.name_norm if domain else None
    if kind == "ip":
        address = db.get(IpAddress, identifier)
        return str(address.address) if address else None
    return None


def _provenance(db: Session, provenance_id: uuid.UUID) -> dict[str, object] | None:
    row = db.get(ProvenanceRecord, provenance_id)
    if row is None:
        return None
    return {
        "id": str(row.id),
        "source_system": row.source_system,
        "source_reference": row.source_reference,
        "collected_at": row.collected_at.isoformat(),
        "method_name": row.method_name,
        "data_classification": row.data_classification,
    }


def source_record(db: Session, case_id: uuid.UUID, kind: str, object_id: uuid.UUID) -> dict[str, object]:
    """One stored source row in this case. Analytical rows are not returned as evidence."""
    missing = Problem(404, "not-found", "Not available", "This record is not available in the case.")
    if kind == "transaction":
        tx = db.get(Transaction, object_id)
        if tx is None or tx.case_id != case_id:
            raise missing
        statement = db.get(Statement, tx.statement_id)
        counterparty = db.get(Account, tx.counterparty_account_id) if tx.counterparty_account_id else None
        return {
            "object_kind": kind,
            "object_id": str(tx.id),
            "data_classification": tx.data_classification,
            "time": {
                "field": "booking_date",
                "value": tx.booking_date.isoformat(),
                "clock": tx.booking_time.isoformat() if tx.booking_time else None,
                "note": "Statement clock as printed. No time zone was supplied, so it is not converted.",
            },
            "record": {
                "subject_account_masked": _mask(db.get(Account, statement.account_id)) if statement else None,
                "line_number": tx.line_number,
                "direction": tx.direction,
                "amount": _money(tx.amount),
                "currency": str(tx.currency).strip(),
                "rail": tx.rail,
                "reference": tx.reference_raw,
                "narration": tx.narration_raw,
                "source_transaction_id": tx.source_transaction_id,
                "counterparty_masked": _mask(counterparty),
                "counterparty_resolution": tx.counterparty_resolution,
                "original_record": tx.original_record,
            },
            "provenance": _provenance(db, tx.provenance_id),
        }
    if kind == "dns_observation":
        dns = db.get(DnsObservation, object_id)
        if dns is None or dns.case_id != case_id:
            raise missing
        domain = db.get(DomainName, dns.domain_id)
        return {
            "object_kind": kind,
            "object_id": str(dns.id),
            "data_classification": dns.data_classification,
            "time": {
                "field": "observed_at",
                "value": dns.observed_at.isoformat(),
                "clock": None,
                "note": "UTC",
            },
            "record": {
                "domain": domain.name_norm if domain else None,
                "rrtype": dns.rrtype,
                "rdata": dns.rdata,
                "resolver": dns.resolver,
            },
            "provenance": _provenance(db, dns.provenance_id),
        }
    if kind == "hosting_observation":
        host = db.get(HostingObservation, object_id)
        if host is None or host.case_id != case_id:
            raise missing
        address = db.get(IpAddress, host.ip_address_id) if host.ip_address_id else None
        return {
            "object_kind": kind,
            "object_id": str(host.id),
            "data_classification": host.data_classification,
            "time": {
                "field": "observed_at",
                "value": host.observed_at.isoformat(),
                "clock": None,
                "note": "UTC",
            },
            "record": {
                "ip": str(address.address) if address else None,
                "provider_name": host.provider_name,
                "source_note": host.source_note,
            },
            "provenance": _provenance(db, host.provenance_id),
        }
    if kind == "gateway_record":
        gateway = db.get(GatewayRecord, object_id)
        if gateway is None or gateway.case_id != case_id:
            raise missing
        domain = db.get(DomainName, gateway.merchant_domain_id)
        return {
            "object_kind": kind,
            "object_id": str(gateway.id),
            "data_classification": gateway.data_classification,
            "time": {
                "field": "processed_at",
                "value": gateway.processed_at.isoformat(),
                "clock": None,
                "note": "UTC, as the gateway record states.",
            },
            "record": {
                "source_record_id": gateway.source_record_id,
                "source_system": gateway.source_system,
                "payment_reference": gateway.payment_reference,
                "payer_account_masked": _mask(db.get(Account, gateway.payer_account_id))
                if gateway.payer_account_id
                else None,
                "payee_account_masked": _mask(db.get(Account, gateway.payee_account_id)),
                "merchant_domain": domain.name_norm if domain else None,
                "merchant_label": gateway.merchant_label,
                "amount": _money(gateway.amount),
                "currency": str(gateway.currency).strip(),
                "original_record": gateway.original_record,
            },
            "provenance": _provenance(db, gateway.provenance_id),
        }
    raise Problem(422, "invalid", "Unknown record kind", "That evidence kind is not recognised.")


def _body(db: Session, row: Relationship, classes: dict[str, Classified]) -> dict[str, object]:
    support = list(
        db.scalars(select(RelationshipSupport).where(RelationshipSupport.relationship_id == row.id))
    )
    reviews = list(
        db.scalars(
            select(RelationshipReview)
            .where(RelationshipReview.relationship_id == row.id)
            .order_by(RelationshipReview.created_at)
        )
    )
    label = classes.get(str(row.id))
    times: list[dict[str, object]] = []
    for item in support:
        try:
            record = source_record(db, row.case_id, item.object_kind, item.object_id)
        except Problem:
            continue
        time_info = record["time"]
        if isinstance(time_info, dict):
            times.append({"object_kind": item.object_kind, "object_id": str(item.object_id), **time_info})
    return {
        "id": str(row.id),
        "analytical_run_id": str(row.analytical_run_id),
        "rel_type": row.rel_type,
        "from_kind": row.from_kind,
        "from_id": str(row.from_id),
        "from_label": endpoint_label(db, row.from_kind, row.from_id),
        "to_kind": row.to_kind,
        "to_id": str(row.to_id),
        "to_label": endpoint_label(db, row.to_kind, row.to_id),
        "assertion_kind": row.assertion_kind,
        "classification": label.classification if label else None,
        "claim": label.claim if label else None,
        "method_version": row.method_version,
        "status": row.status,
        "limitation": row.limitation,
        "explanation": row.explanation,
        "temporal_context": times,
        "support": [{"object_kind": item.object_kind, "object_id": str(item.object_id)} for item in support],
        "reviews": [
            {
                "decision": item.decision,
                "reason": item.reason,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in reviews
        ],
    }


def decide(
    db: Session,
    principal: Principal,
    relationship_id: uuid.UUID,
    decision: str,
    reason: str,
    request_id: str | None,
) -> dict[str, object]:
    row = db.get(Relationship, relationship_id)
    if row is None:
        raise Problem(404, "not-found", "Not available", "This relationship is not available.")
    _mutate(db, principal, row.case_id, request_id)
    if row.status != "proposed":
        raise Problem(409, "conflict", "Already decided", "This relationship already has a decision.")
    note = reason.strip() or "No reason recorded."
    if len(note) > 2000:
        raise Problem(
            422, "invalid", "Reason too long", "The review reason must be 2000 characters or fewer."
        )
    row.status = decision
    row.decided_by = principal.id
    row.decided_at = datetime.now(UTC)
    db.add(
        RelationshipReview(
            relationship_id=row.id,
            case_id=row.case_id,
            decision=decision,
            reason=note,
            decided_by=principal.id,
        )
    )
    append_audit(
        db,
        action="relationship.decide",
        outcome="success",
        object_kind="relationship",
        actor_id=principal.id,
        case_id=row.case_id,
        object_id=str(row.id),
        request_id=request_id,
        detail={"status": decision, "rel_type": row.rel_type, "assertion_kind": row.assertion_kind},
    )
    db.flush()
    return _body(db, row, classifications(db, row.case_id))
