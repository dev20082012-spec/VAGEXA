"""Bounded reads that assemble one investigation from stored rows. Nothing here computes a finding."""

import uuid
from collections import Counter
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.models import (
    Account,
    AccountIndicator,
    AnalyticalRun,
    AuditEvent,
    Case,
    CaseAssignment,
    DnsObservation,
    DomainName,
    Finding,
    GatewayRecord,
    HostingObservation,
    IpAddress,
    Relationship,
    Statement,
    TraceFlow,
    TraceResidual,
    Transaction,
)
from vagexa.api.errors import Problem
from vagexa.application import correlation_service
from vagexa.application.auth_service import Principal
from vagexa.domain.authorization import case_role_allows

LIMIT = 200
CROSS_DOMAIN = {"gateway_merchant", "mentioned_in"}
SUMMARY_LIMITATION = (
    "Every figure is a count of stored rows in this case. A trace layer is a fifo.v1 allocation. "
    "An indicator is a rule match. A relationship is a proposal until an investigator decides it. "
    "None of these is a finding of guilt, ownership, or identity."
)
SYNTHETIC_NOTICE = (
    "Synthetic demonstration data. These accounts, domains, addresses, and gateway records are "
    "fictional and are not official records."
)


def _readable(db: Session, principal: Principal, case_id: uuid.UUID, permission: str = "cases.read") -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None or not case_role_allows(assignment.case_role, permission):
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    return case


def _mask(account: Account | None) -> str | None:
    if account is None:
        return None
    key = account.account_number_norm or account.vpa_norm or ""
    return f"****{key[-4:]}" if key else None


def _count(db: Session, model: type, case_id: uuid.UUID) -> int:
    column = model.case_id  # type: ignore[attr-defined]
    return int(db.scalar(select(func.count()).select_from(model).where(column == case_id)) or 0)


def summary(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    case = _readable(db, principal, case_id)
    trace = db.scalar(
        select(AnalyticalRun)
        .where(
            AnalyticalRun.case_id == case.id,
            AnalyticalRun.run_kind == "trace",
            AnalyticalRun.status == "succeeded",
        )
        .order_by(AnalyticalRun.created_at.desc())
    )
    latest_trace: dict[str, object] | None = None
    if trace is not None:
        flow_count = int(
            db.scalar(
                select(func.count()).select_from(TraceFlow).where(TraceFlow.analytical_run_id == trace.id)
            )
            or 0
        )
        residuals = list(db.scalars(select(TraceResidual).where(TraceResidual.analytical_run_id == trace.id)))
        latest_trace = {
            "id": str(trace.id),
            "method_version": trace.method_version,
            "max_layer": trace.parameters.get("max_layer"),
            "flow_count": flow_count,
            "residuals": [
                {
                    "account_masked": _mask(db.get(Account, item.account_id)),
                    "amount": f"{Decimal(str(item.amount)):.4f}",
                    "currency": str(item.currency).strip(),
                    "reason": item.reason,
                }
                for item in residuals
            ],
        }
    indicator_run = db.scalar(
        select(AnalyticalRun)
        .where(
            AnalyticalRun.case_id == case.id,
            AnalyticalRun.run_kind == "indicators",
            AnalyticalRun.status == "succeeded",
        )
        .order_by(AnalyticalRun.created_at.desc())
    )
    indicators: list[dict[str, object]] = []
    if indicator_run is not None:
        for row in db.scalars(
            select(AccountIndicator).where(AccountIndicator.analytical_run_id == indicator_run.id)
        ):
            indicators.append(
                {
                    "code": row.code,
                    "account_masked": _mask(db.get(Account, row.account_id)),
                    "support_count": len(row.support_transaction_ids),
                    "assertion_kind": row.assertion_kind,
                }
            )
    relationships = list(
        db.scalars(
            select(Relationship)
            .where(Relationship.case_id == case.id)
            .order_by(Relationship.created_at, Relationship.id)
        )
    )
    classes = correlation_service.classifications(db, case.id)
    by_class = Counter(classes[str(row.id)].classification for row in relationships if str(row.id) in classes)
    cross = Counter(
        classes[str(row.id)].classification
        for row in relationships
        if str(row.id) in classes and row.rel_type in CROSS_DOMAIN
    )
    key = [
        {
            "id": str(row.id),
            "rel_type": row.rel_type,
            "classification": classes[str(row.id)].classification if str(row.id) in classes else None,
            "from_label": correlation_service.endpoint_label(db, row.from_kind, row.from_id),
            "to_label": correlation_service.endpoint_label(db, row.to_kind, row.to_id),
            "status": row.status,
        }
        for row in relationships
        if row.rel_type != "same_payment"
    ][:10]
    activity = [
        {"action": row.action, "outcome": row.outcome, "occurred_at": row.occurred_at.isoformat()}
        for row in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.case_id == case.id)
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
            .limit(10)
        )
    ]
    return {
        "case": {
            "id": str(case.id),
            "reference": case.reference,
            "title": case.title,
            "status": case.status,
            "data_classification": case.data_classification,
            "opened_on": case.opened_on.isoformat(),
        },
        "synthetic_notice": SYNTHETIC_NOTICE if case.data_classification == "synthetic" else None,
        "counts": {
            "statements": _count(db, Statement, case.id),
            "transactions": _count(db, Transaction, case.id),
            "dns_observations": _count(db, DnsObservation, case.id),
            "hosting_observations": _count(db, HostingObservation, case.id),
            "gateway_records": _count(db, GatewayRecord, case.id),
            "findings": _count(db, Finding, case.id),
            "relationships": len(relationships),
        },
        "relationships_by_classification": dict(sorted(by_class.items())),
        "cross_domain_by_classification": dict(sorted(cross.items())),
        "overlap_count": sum(1 for row in relationships if row.rel_type == "infrastructure_overlap"),
        "latest_trace": latest_trace,
        "indicators": indicators,
        "key_relationships": key,
        "recent_activity": activity,
        "limitations": SUMMARY_LIMITATION,
    }


def entities(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    case = _readable(db, principal, case_id)
    subject_rows = db.execute(
        select(Statement.account_id, func.count(Transaction.id))
        .join(Transaction, Transaction.statement_id == Statement.id)
        .where(Statement.case_id == case.id)
        .group_by(Statement.account_id)
    ).all()
    subjects = {account_id: int(count) for account_id, count in subject_rows}
    counterparty_ids = set(
        db.scalars(
            select(Transaction.counterparty_account_id).where(
                Transaction.case_id == case.id, Transaction.counterparty_account_id.is_not(None)
            )
        ).all()
    )
    account_ids = set(subjects) | {item for item in counterparty_ids if item is not None}
    accounts = (
        list(db.scalars(select(Account).where(Account.id.in_(account_ids)).limit(LIMIT)))
        if account_ids
        else []
    )
    dns_rows = db.execute(
        select(DomainName, func.count(DnsObservation.id))
        .join(DnsObservation, DnsObservation.domain_id == DomainName.id)
        .where(DnsObservation.case_id == case.id)
        .group_by(DomainName.id)
        .limit(LIMIT)
    ).all()
    gateway_domains = set(
        db.scalars(select(GatewayRecord.merchant_domain_id).where(GatewayRecord.case_id == case.id)).all()
    )
    domain_counts = {domain.id: (domain, int(count)) for domain, count in dns_rows}
    for domain_id in gateway_domains - set(domain_counts):
        domain = db.get(DomainName, domain_id)
        if domain is not None:
            domain_counts[domain.id] = (domain, 0)
    ip_ids = set(
        db.scalars(
            select(DnsObservation.ip_address_id).where(
                DnsObservation.case_id == case.id, DnsObservation.ip_address_id.is_not(None)
            )
        ).all()
    )
    ip_ids |= set(
        db.scalars(
            select(HostingObservation.ip_address_id).where(
                HostingObservation.case_id == case.id, HostingObservation.ip_address_id.is_not(None)
            )
        ).all()
    )
    addresses = (
        list(db.scalars(select(IpAddress).where(IpAddress.id.in_(ip_ids)).limit(LIMIT))) if ip_ids else []
    )
    return {
        "data_classification": case.data_classification,
        "accounts": sorted(
            [
                {
                    "id": str(row.id),
                    "masked": _mask(row),
                    "role": "statement_subject" if row.id in subjects else "counterparty_only",
                    "statement_rows": subjects.get(row.id, 0),
                }
                for row in accounts
            ],
            key=lambda item: str(item["masked"]),
        ),
        "domains": sorted(
            [
                {
                    "id": str(domain.id),
                    "name": domain.name_norm,
                    "dns_observations": count,
                    "in_gateway_record": domain.id in gateway_domains,
                }
                for domain, count in domain_counts.values()
            ],
            key=lambda item: str(item["name"]),
        ),
        "ip_addresses": sorted(
            [{"id": str(row.id), "address": str(row.address)} for row in addresses],
            key=lambda item: item["address"],
        ),
        "note": "Accounts are instrument keys. A domain is a name. Neither identifies a person.",
    }


def audit_events(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    case = _readable(db, principal, case_id, "audit.read")
    rows = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.case_id == case.id)
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
            .limit(50)
        )
    )
    return {
        "items": [
            {
                "action": row.action,
                "outcome": row.outcome,
                "object_kind": row.object_kind,
                "occurred_at": row.occurred_at.isoformat(),
            }
            for row in rows
        ]
    }


def evidence(
    db: Session, principal: Principal, case_id: uuid.UUID, object_kind: str, object_id: uuid.UUID
) -> dict[str, object]:
    case = _readable(db, principal, case_id)
    return correlation_service.source_record(db, case.id, object_kind, object_id)
