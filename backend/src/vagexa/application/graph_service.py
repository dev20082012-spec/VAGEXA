"""Load one case and return the derived graph. The graph is not stored."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
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
    HostingObservation,
    IpAddress,
    Relationship,
    RelationshipSupport,
    Statement,
    TraceFlow,
    TraceResidual,
    Transaction,
)
from vagexa.api.errors import Problem
from vagexa.application import correlation_service
from vagexa.application.auth_service import Principal
from vagexa.domain.authorization import case_role_allows
from vagexa.intelligence.digital.normalise import OVERLAP_LIMITATION
from vagexa.intelligence.graph.build import (
    GraphFlow,
    GraphLeg,
    GraphResidual,
    InfraObservation,
    build_graph,
)

FOUR = Decimal("0.0001")
SIGNAL_LIMITATION = "Same normalised key. Not a finding that the holders are the same person."


def _readable(
    db: Session, principal: Principal, case_id: uuid.UUID, action: str, request_id: str | None
) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None or not case_role_allows(assignment.case_role, "cases.read"):
        append_audit(
            db,
            action=action,
            outcome="denied",
            object_kind="case",
            actor_id=principal.id,
            case_id=case.id if case and assignment else None,
            object_id=str(case_id),
            request_id=request_id,
        )
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    return case


def _mask(account: Account) -> str:
    number = account.account_number_norm or account.vpa_norm or ""
    return f"****{number[-4:]}" if number else "****"


def _current_transactions(db: Session, case_id: uuid.UUID) -> list[tuple[Transaction, uuid.UUID, str]]:
    superseded = select(Statement.supersedes_statement_id).where(
        Statement.supersedes_statement_id.is_not(None)
    )
    rows = db.execute(
        select(Transaction, Statement.account_id, Statement.parser_version)
        .join(Statement, Statement.id == Transaction.statement_id)
        .where(Transaction.case_id == case_id, Statement.id.not_in(superseded))
    ).all()
    return [(tx, account_id, parser_version) for tx, account_id, parser_version in rows]


def _cited_accounts(rows: list[tuple[Transaction, uuid.UUID, str]]) -> set[uuid.UUID]:
    cited: set[uuid.UUID] = set()
    for tx, account_id, _parser in rows:
        cited.add(account_id)
        if tx.counterparty_account_id:
            cited.add(tx.counterparty_account_id)
    return cited


def case_graph(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    focus: uuid.UUID | None,
    max_hops: int,
    trace_id: uuid.UUID | None,
    path_from: uuid.UUID | None,
    path_to: uuid.UUID | None,
    booking_date_from: date | None,
    booking_date_to: date | None,
    request_id: str | None,
) -> dict[str, object]:
    case = _readable(db, principal, case_id, "graph.read", request_id)
    if max_hops < 1 or max_hops > 5:
        raise Problem(422, "invalid", "Hop limit", "Hops must be from 1 to 5.")
    rows = _current_transactions(db, case.id)
    if booking_date_from or booking_date_to:
        rows = [
            row
            for row in rows
            if (booking_date_from is None or row[0].booking_date >= booking_date_from)
            and (booking_date_to is None or row[0].booking_date <= booking_date_to)
        ]
    cited = _cited_accounts(rows)
    if focus is not None and focus not in cited:
        raise Problem(404, "not-found", "Not available", "This account is not available in the case.")
    evidence = {
        row.object_id: row.id
        for row in db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.case_id == case.id,
                EvidenceRecord.kind == "transaction",
            )
        )
    }
    legs = [
        GraphLeg(
            transaction_id=str(tx.id),
            account_id=str(account_id),
            direction=tx.direction,
            counterparty_account_id=str(tx.counterparty_account_id) if tx.counterparty_account_id else None,
            counterparty_resolution=tx.counterparty_resolution,
            amount=Decimal(str(tx.amount)).quantize(FOUR),
            currency=str(tx.currency).strip(),
            booking_date=tx.booking_date,
            booking_time=tx.booking_time,
            provenance_id=str(tx.provenance_id),
            evidence_id=str(evidence[tx.id]) if tx.id in evidence else None,
            reference=tx.reference_raw,
            rail=tx.rail,
            method_version=parser_version,
        )
        for tx, account_id, parser_version in rows
    ]
    run = _trace_run(db, case.id, trace_id)
    flows: list[GraphFlow] = []
    residuals: list[GraphResidual] = []
    if run is not None:
        tx_dates = {tx.id: tx.booking_date for tx, _account, _parser in rows}
        for flow in db.scalars(select(TraceFlow).where(TraceFlow.analytical_run_id == run.id)):
            booked = tx_dates.get(flow.source_transaction_id)
            if booking_date_from or booking_date_to:
                if booked is None:
                    continue
                if booking_date_from and booked < booking_date_from:
                    continue
                if booking_date_to and booked > booking_date_to:
                    continue
            flows.append(
                GraphFlow(
                    flow_id=str(flow.id),
                    from_account_id=str(flow.from_account_id),
                    to_account_id=str(flow.to_account_id) if flow.to_account_id else None,
                    exit_kind=flow.exit_kind,
                    amount=Decimal(str(flow.amount)).quantize(FOUR),
                    currency=str(flow.currency).strip(),
                    layer_to=flow.layer_to,
                    assertion_kind=flow.assertion_kind,
                    method_name=flow.method_name,
                    method_version=flow.method_version,
                    source_transaction_id=str(flow.source_transaction_id),
                    trace_run_id=str(run.id),
                    booking_date=booked,
                )
            )
        for residual in db.scalars(select(TraceResidual).where(TraceResidual.analytical_run_id == run.id)):
            residuals.append(
                GraphResidual(
                    account_id=str(residual.account_id),
                    amount=Decimal(str(residual.amount)).quantize(FOUR),
                    currency=str(residual.currency).strip(),
                    reason=residual.reason,
                    trace_run_id=str(run.id),
                )
            )
    accounts = (
        {str(row.id): row for row in db.scalars(select(Account).where(Account.id.in_(cited)))}
        if cited
        else {}
    )
    labels = {account_id: _mask(account) for account_id, account in accounts.items()}
    payload = build_graph(
        legs,
        flows,
        residuals,
        labels=labels,
        data_classification=case.data_classification,
        focus=str(focus) if focus else None,
        max_hops=max_hops,
        path_from=str(path_from) if path_from else None,
        path_to=str(path_to) if path_to else None,
        observations=_infra(db, case.id),
    )
    append_audit(
        db,
        action="graph.read",
        outcome="success",
        object_kind="case",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(case.id),
        request_id=request_id,
        detail={"max_hops": max_hops, "node_count": len(payload.nodes), "truncated": payload.truncated},
    )
    body = {
        "bounds": {
            "case_id": str(case.id),
            "focus": str(focus) if focus else None,
            "max_hops": max_hops,
            "trace_id": str(run.id) if run else None,
        },
        "truncated": payload.truncated,
        "limitations": payload.limitations,
        "nodes": [
            {
                "id": node.id,
                "kind": node.kind,
                "label": node.label,
                "data_classification": node.data_classification,
                "residuals": node.residuals,
            }
            for node in payload.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "from": edge.source,
                "to": edge.target,
                "kind": edge.kind,
                "assertion_kind": edge.assertion_kind,
                "method_name": edge.method_name,
                "method_version": edge.method_version,
                "amount": edge.amount,
                "currency": edge.currency,
                "booking_date": edge.booking_date,
                "provenance_id": edge.provenance_id,
                "evidence_ids": edge.evidence_ids,
                "source_transaction_ids": edge.source_transaction_ids,
                "layer_to": edge.layer_to,
                "trace_run_id": edge.trace_run_id,
                "explanation": edge.explanation,
                "support": edge.support,
                "relationship_id": None,
                "classification": None,
                "status": None,
            }
            for edge in payload.edges
        ],
        "components": payload.components,
        "path": payload.path,
        "path_reason": payload.path_reason,
    }
    nodes_out: list[dict[str, object]] = body["nodes"]  # type: ignore[assignment]
    edges_out: list[dict[str, object]] = body["edges"]  # type: ignore[assignment]
    node_ids = {str(node["id"]) for node in nodes_out}
    extra_nodes, extra_edges = correlation_edges(
        db, case.id, node_ids, case.data_classification, allow_new_nodes=focus is None
    )
    nodes_out.extend(extra_nodes)
    edges_out.extend(extra_edges)
    return body


def _graph_endpoint(kind: str, identifier: uuid.UUID) -> str:
    if kind == "account":
        return str(identifier)
    return f"{kind}:{identifier}"


def correlation_edges(
    db: Session,
    case_id: uuid.UUID,
    node_ids: set[str],
    data_classification: str,
    *,
    allow_new_nodes: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Cross-domain edges. same_payment is omitted because the transfer edge already cites both rows."""
    rows = list(
        db.scalars(
            select(Relationship).where(
                Relationship.case_id == case_id,
                Relationship.status != "rejected",
                Relationship.rel_type.in_(["mentioned_in", "gateway_merchant"]),
            )
        )
    )
    if not rows:
        return [], []
    classes = correlation_service.classifications(db, case_id)
    supports = list(
        db.scalars(
            select(RelationshipSupport).where(
                RelationshipSupport.relationship_id.in_([row.id for row in rows])
            )
        )
    )
    by_rel: dict[uuid.UUID, list[RelationshipSupport]] = {}
    for item in supports:
        by_rel.setdefault(item.relationship_id, []).append(item)
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    for row in rows:
        source = _graph_endpoint(row.from_kind, row.from_id)
        target = _graph_endpoint(row.to_kind, row.to_id)
        for endpoint, kind, identifier in (
            (source, row.from_kind, row.from_id),
            (target, row.to_kind, row.to_id),
        ):
            if endpoint in node_ids or not allow_new_nodes:
                continue
            node_label = correlation_service.endpoint_label(db, kind, identifier)
            if node_label is None:
                continue
            nodes.append(
                {
                    "id": endpoint,
                    "kind": kind,
                    "label": node_label,
                    "data_classification": data_classification,
                    "residuals": [],
                }
            )
            node_ids.add(endpoint)
        if source not in node_ids or target not in node_ids:
            continue
        items = sorted(by_rel.get(row.id, []), key=lambda item: (item.object_kind, str(item.object_id)))
        classified = classes.get(str(row.id))
        edges.append(
            {
                "id": f"rel:{row.id}",
                "from": source,
                "to": target,
                "kind": row.rel_type,
                "assertion_kind": row.assertion_kind,
                "method_name": row.method_name,
                "method_version": row.method_version,
                "amount": "",
                "currency": "",
                "booking_date": None,
                "provenance_id": str(row.provenance_id),
                "evidence_ids": [str(item.object_id) for item in items if item.object_kind != "transaction"],
                "source_transaction_ids": [
                    str(item.object_id) for item in items if item.object_kind == "transaction"
                ],
                "layer_to": None,
                "trace_run_id": None,
                "explanation": row.explanation,
                "support": [
                    {"object_kind": item.object_kind, "object_id": str(item.object_id)} for item in items
                ],
                "relationship_id": str(row.id),
                "classification": classified.classification if classified else None,
                "status": row.status,
            }
        )
    return nodes, edges


def _infra(db: Session, case_id: uuid.UUID) -> list[InfraObservation]:
    dns_rows = db.execute(
        select(DnsObservation, DomainName, IpAddress)
        .join(DomainName, DomainName.id == DnsObservation.domain_id)
        .join(IpAddress, IpAddress.id == DnsObservation.ip_address_id)
        .where(DnsObservation.case_id == case_id)
    ).all()
    hosting_rows = db.execute(
        select(HostingObservation, IpAddress)
        .join(IpAddress, IpAddress.id == HostingObservation.ip_address_id, isouter=True)
        .where(HostingObservation.case_id == case_id)
    ).all()
    observations = [
        InfraObservation(
            kind="dns",
            observation_id=str(row.id),
            provenance_id=str(row.provenance_id),
            observed_at=row.observed_at.isoformat(),
            domain_id=str(domain.id),
            domain_name=domain.name_norm,
            ip_id=str(address.id),
            ip_label=str(address.address),
            rrtype=row.rrtype,
        )
        for row, domain, address in dns_rows
    ]
    for row, address in hosting_rows:
        observations.append(
            InfraObservation(
                kind="hosting",
                observation_id=str(row.id),
                provenance_id=str(row.provenance_id),
                observed_at=row.observed_at.isoformat(),
                ip_id=str(address.id) if address is not None else None,
                ip_label=str(address.address) if address is not None else None,
                provider_name=row.provider_name,
            )
        )
    return observations


def _trace_run(db: Session, case_id: uuid.UUID, trace_id: uuid.UUID | None) -> AnalyticalRun | None:
    if trace_id is None:
        return db.scalar(
            select(AnalyticalRun)
            .where(
                AnalyticalRun.case_id == case_id,
                AnalyticalRun.run_kind == "trace",
                AnalyticalRun.status == "succeeded",
            )
            .order_by(AnalyticalRun.created_at.desc())
        )
    run = db.get(AnalyticalRun, trace_id)
    if run is None or run.case_id != case_id or run.run_kind != "trace" or run.status != "succeeded":
        raise Problem(404, "not-found", "Not available", "This trace is not available.")
    return run


def cross_case_signals(
    db: Session, principal: Principal, case_id: uuid.UUID, request_id: str | None
) -> dict[str, object]:
    case = _readable(db, principal, case_id, "cross_case.lookup", request_id)
    rows = _current_transactions(db, case.id)
    cited = _cited_accounts(rows)
    items: list[dict[str, object]] = []
    if cited:
        superseded = select(Statement.supersedes_statement_id).where(
            Statement.supersedes_statement_id.is_not(None)
        )
        subject_cases = select(Statement.case_id, Statement.account_id.label("account_id")).where(
            Statement.account_id.in_(cited), Statement.id.not_in(superseded)
        )
        counterparty_cases = (
            select(Transaction.case_id, Transaction.counterparty_account_id.label("account_id"))
            .join(Statement, Statement.id == Transaction.statement_id)
            .where(
                Transaction.counterparty_account_id.in_(cited),
                Statement.id.not_in(superseded),
            )
        )
        union = subject_cases.union(counterparty_cases).subquery()
        counts = db.execute(
            select(union.c.account_id, func.count(func.distinct(union.c.case_id)))
            .where(union.c.case_id != case.id)
            .group_by(union.c.account_id)
        ).all()
        accounts = {row.id: row for row in db.scalars(select(Account).where(Account.id.in_(cited)))}
        for account_id, count in counts:
            if int(count) < 1:
                continue
            account = accounts.get(account_id)
            if account is None:
                continue
            items.append(
                {
                    "identifier_kind": "account",
                    "masked": _mask(account),
                    "other_case_count": int(count),
                    "assertion_kind": "inferred",
                    "method": "exact_identifier",
                    "limitations": SIGNAL_LIMITATION,
                }
            )
    items.extend(_indicator_signals(db, case.id))
    items.sort(key=lambda item: (str(item["identifier_kind"]), str(item["masked"])))
    append_audit(
        db,
        action="cross_case.lookup",
        outcome="success",
        object_kind="case",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(case.id),
        request_id=request_id,
        detail={"signal_count": len(items)},
    )
    return {"items": items}


def _indicator_signals(db: Session, case_id: uuid.UUID) -> list[dict[str, object]]:
    domain_ids = set(
        db.scalars(select(DnsObservation.domain_id).where(DnsObservation.case_id == case_id)).all()
    )
    signals: list[dict[str, object]] = []
    if domain_ids:
        counts = db.execute(
            select(DnsObservation.domain_id, func.count(func.distinct(DnsObservation.case_id)))
            .where(DnsObservation.domain_id.in_(domain_ids), DnsObservation.case_id != case_id)
            .group_by(DnsObservation.domain_id)
        ).all()
        names = {
            row.id: row.name_norm
            for row in db.scalars(select(DomainName).where(DomainName.id.in_(domain_ids)))
        }
        for domain_id, count in counts:
            if int(count) < 1 or domain_id not in names:
                continue
            signals.append(
                {
                    "identifier_kind": "domain",
                    "masked": names[domain_id],
                    "other_case_count": int(count),
                    "assertion_kind": "inferred",
                    "method": "exact_identifier",
                    "limitations": OVERLAP_LIMITATION,
                }
            )
    return signals
