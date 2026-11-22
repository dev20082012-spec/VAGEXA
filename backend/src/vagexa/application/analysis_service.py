"""Run the approved analytical methods and store the result. Routers do not allocate."""

import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import (
    Account,
    AccountIndicator,
    AnalyticalRun,
    Case,
    CaseAssignment,
    EvidenceRecord,
    Finding,
    FindingSupport,
    Job,
    Statement,
    TraceFlow,
    TraceResidual,
    TraceSeed,
    Transaction,
)
from vagexa.api.errors import Problem
from vagexa.application.auth_service import Principal
from vagexa.domain.authorization import case_role_allows
from vagexa.intelligence.financial.activity import summarise
from vagexa.intelligence.financial.fifo import METHOD_VERSION as FIFO_VERSION
from vagexa.intelligence.financial.fifo import Seed, trace
from vagexa.intelligence.financial.indicators import METHOD_VERSION as INDICATOR_VERSION
from vagexa.intelligence.financial.indicators import detect
from vagexa.intelligence.financial.ledger import LedgerRow, sort_key
from vagexa.intelligence.financial.walk import METHOD_VERSION as WALK_VERSION
from vagexa.intelligence.financial.walk import walk_statements

FOUR = Decimal("0.0001")


def _require_analysis(
    db: Session, principal: Principal, case_id: uuid.UUID, request_id: str | None, action: str
) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None or not case_role_allows(assignment.case_role, "analysis.run"):
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
        if case is None or assignment is None:
            raise Problem(404, "not-found", "Not available", "This case is not available.")
        raise Problem(403, "forbidden", "Not allowed", "You cannot run analysis on this case.")
    return case


def _require_read(db: Session, principal: Principal, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None or not case_role_allows(assignment.case_role, "cases.read"):
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    return case


def _load(db: Session, case_id: uuid.UUID) -> tuple[list[LedgerRow], set[str]]:
    superseded = select(Statement.supersedes_statement_id).where(
        Statement.supersedes_statement_id.is_not(None)
    )
    pairs = db.execute(
        select(Transaction, Statement.account_id)
        .join(Statement, Statement.id == Transaction.statement_id)
        .where(Transaction.case_id == case_id, Statement.id.not_in(superseded))
    ).all()
    rows: list[LedgerRow] = []
    subjects: set[str] = set()
    for tx, account_id in pairs:
        subjects.add(str(account_id))
        rows.append(
            LedgerRow(
                id=str(tx.id),
                account_id=str(account_id),
                direction=tx.direction,
                amount=Decimal(str(tx.amount)).quantize(FOUR),
                currency=str(tx.currency).strip(),
                booking_date=tx.booking_date,
                booking_time=tx.booking_time,
                line_number=tx.line_number,
                counterparty_account_id=str(tx.counterparty_account_id)
                if tx.counterparty_account_id
                else None,
                counterparty_resolution=tx.counterparty_resolution,
                reference=tx.reference_raw,
                rail=tx.rail,
                time_precision=tx.time_precision,
            )
        )
    return rows, subjects


def _input_hash(rows: list[LedgerRow], parameters: dict[str, object]) -> str:
    snapshot = [
        {
            "account_id": row.account_id,
            "amount": f"{row.amount:.4f}",
            "booking_date": row.booking_date.isoformat(),
            "booking_time": row.booking_time.isoformat() if row.booking_time else None,
            "counterparty_account_id": row.counterparty_account_id,
            "counterparty_resolution": row.counterparty_resolution,
            "currency": row.currency,
            "direction": row.direction,
            "id": row.id,
            "line_number": row.line_number,
            "rail": row.rail,
            "reference": row.reference,
        }
        for row in sorted(rows, key=sort_key)
    ]
    encoded = json.dumps({"parameters": parameters, "rows": snapshot}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _accounts(db: Session, identifiers: set[str]) -> dict[str, Account]:
    if not identifiers:
        return {}
    parsed = [uuid.UUID(item) for item in identifiers]
    return {str(row.id): row for row in db.scalars(select(Account).where(Account.id.in_(parsed)))}


def _mask(account: Account | None) -> str | None:
    if account is None:
        return None
    number = account.account_number_norm or account.vpa_norm
    if not number:
        return None
    return f"****{number[-4:]}"


def _tail(account: Account | None) -> str:
    masked = _mask(account)
    return masked[-4:] if masked else "unknown"


def _evidence(db: Session, case_id: uuid.UUID, tx: Transaction) -> EvidenceRecord:
    found = db.scalar(
        select(EvidenceRecord).where(
            EvidenceRecord.case_id == case_id,
            EvidenceRecord.kind == "transaction",
            EvidenceRecord.object_id == tx.id,
        )
    )
    if found is not None:
        return found
    digest = hashlib.sha256(
        f"{tx.id}|{Decimal(str(tx.amount)).quantize(FOUR):.4f}|{str(tx.currency).strip()}|{tx.direction}|{tx.booking_date.isoformat()}".encode()
    ).hexdigest()
    row = EvidenceRecord(
        case_id=case_id,
        provenance_id=tx.provenance_id,
        kind="transaction",
        object_id=tx.id,
        content_hash=digest,
    )
    db.add(row)
    db.flush()
    return row


def _finding(
    db: Session,
    run: AnalyticalRun,
    *,
    kind: str,
    summary: str,
    assertion_kind: str,
    limitations: str,
    method_name: str,
    method_version: str,
    transactions: list[Transaction],
) -> Finding:
    finding = Finding(
        analytical_run_id=run.id,
        case_id=run.case_id,
        finding_kind=kind,
        summary=summary,
        assertion_kind=assertion_kind,
        limitations=limitations,
        method_name=method_name,
        method_version=method_version,
    )
    db.add(finding)
    db.flush()
    seen: set[uuid.UUID] = set()
    for tx in transactions:
        evidence = _evidence(db, run.case_id, tx)
        if evidence.id in seen:
            continue
        seen.add(evidence.id)
        db.add(FindingSupport(finding_id=finding.id, evidence_id=evidence.id))
    return finding


def _job(db: Session, case_id: uuid.UUID, kind: str, run: AnalyticalRun) -> Job:
    job = Job(
        kind=kind,
        case_id=case_id,
        payload={
            "analytical_run_id": str(run.id),
            "method_version": run.method_version,
            "status": run.status,
            "error_code": run.error_code,
        },
        status="succeeded" if run.status == "succeeded" else "failed",
        error_code=run.error_code,
        finished_at=datetime.now(UTC),
    )
    db.add(job)
    db.flush()
    return job


def _transactions(db: Session, identifiers: list[str]) -> dict[str, Transaction]:
    if not identifiers:
        return {}
    parsed = [uuid.UUID(item) for item in identifiers]
    return {str(row.id): row for row in db.scalars(select(Transaction).where(Transaction.id.in_(parsed)))}


def _gap(left: LedgerRow | None, right: LedgerRow | None) -> str | None:
    if left is None or right is None:
        return None
    if left.time_precision != "time" or right.time_precision != "time":
        return None
    if left.booking_time is None or right.booking_time is None:
        return None
    start = datetime.combine(left.booking_date, left.booking_time)
    end = datetime.combine(right.booking_date, right.booking_time)
    delta = end - start
    seconds = (
        Decimal(delta.days) * Decimal(86400)
        + Decimal(delta.seconds)
        + (Decimal(delta.microseconds) / Decimal(1_000_000))
    )
    return f"{(seconds / Decimal(3600)).quantize(FOUR):.4f}"


def _decimal(raw: str, field_name: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise Problem(422, "invalid", "Invalid amount", "Amounts must be decimals.") from exc
    if value < 0:
        raise Problem(422, "invalid", "Invalid amount", f"{field_name} cannot be negative.")
    return value


def run_trace(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    seed_transaction_ids: list[uuid.UUID],
    max_layer: int,
    currency: str,
    request_id: str | None,
    fault_extra_outflow: Decimal | None = None,
) -> dict[str, object]:
    case = _require_analysis(db, principal, case_id, request_id, "trace.run")
    if not seed_transaction_ids:
        raise Problem(422, "invalid", "Seed required", "Choose at least one transaction.")
    rows, subjects = _load(db, case_id)
    by_id = {row.id: row for row in rows}
    seeds: list[Seed] = []
    for seed_id in seed_transaction_ids:
        row = by_id.get(str(seed_id))
        if row is None:
            raise Problem(404, "not-found", "Not available", "This transaction is not available.")
        if row.currency != currency:
            raise Problem(
                422, "invalid", "Currency mismatch", "The seed currency does not match the trace currency."
            )
        seeds.append(Seed(str(seed_id)))
    parameters: dict[str, object] = {
        "currency": currency,
        "max_layer": max_layer,
        "policy": "fifo",
        "policy_version": FIFO_VERSION,
        "seed_count": len(seeds),
    }
    result = trace(
        rows,
        seeds,
        max_layer=max_layer,
        currency=currency,
        statement_account_ids=subjects,
        fault_extra_outflow=fault_extra_outflow,
    )
    run = AnalyticalRun(
        case_id=case.id,
        run_kind="trace",
        method_name="fifo",
        method_version=FIFO_VERSION,
        parameters=parameters,
        input_hash=_input_hash(rows, parameters),
        output_hash=result.output_hash,
        status=result.status,
        error_code=result.error_code,
        requested_by=principal.id,
    )
    db.add(run)
    db.flush()
    for seed in seeds:
        db.add(TraceSeed(analytical_run_id=run.id, transaction_id=uuid.UUID(seed.transaction_id)))
    tx_ids = [item.source_transaction_id for item in result.flows]
    transactions = _transactions(db, tx_ids)
    if result.status == "succeeded":
        for item in result.flows:
            db.add(
                TraceFlow(
                    analytical_run_id=run.id,
                    case_id=case.id,
                    from_account_id=uuid.UUID(item.from_account_id),
                    to_account_id=uuid.UUID(item.to_account_id) if item.to_account_id else None,
                    exit_kind=item.exit_kind,
                    source_transaction_id=uuid.UUID(item.source_transaction_id),
                    amount=item.amount,
                    currency=item.currency,
                    layer_to=item.layer_to,
                    assertion_kind=item.assertion_kind,
                    method_name=item.method_name,
                    method_version=FIFO_VERSION,
                    origin_complaint_id=None,
                )
            )
        for residual in result.residuals:
            db.add(
                TraceResidual(
                    analytical_run_id=run.id,
                    account_id=uuid.UUID(residual.account_id),
                    amount=residual.amount,
                    currency=residual.currency,
                    reason=residual.reason,
                )
            )
        _finding(
            db,
            run,
            kind="trace",
            summary=(
                f"fifo.v1 allocated flows inside the supplied statements at horizon {max_layer}. "
                "This is not a finding of guilt."
            ),
            assertion_kind="inferred",
            limitations=result.limitations,
            method_name="fifo",
            method_version=FIFO_VERSION,
            transactions=[transactions[item] for item in tx_ids if item in transactions],
        )
    job = _job(db, case.id, "trace", run)
    append_audit(
        db,
        action="trace.run",
        outcome="success" if result.status == "succeeded" else "failure",
        object_kind="analytical_run",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(run.id),
        request_id=request_id,
        detail={
            "method_version": FIFO_VERSION,
            "max_layer": max_layer,
            "status": result.status,
            "flow_count": len(result.flows),
            "data_classification": case.data_classification,
        },
    )
    return trace_body(db, run, job_id=job.id)


def trace_body(db: Session, run: AnalyticalRun, job_id: uuid.UUID | None = None) -> dict[str, object]:
    flows = list(
        db.scalars(
            select(TraceFlow)
            .where(TraceFlow.analytical_run_id == run.id)
            .order_by(TraceFlow.layer_to, TraceFlow.id)
        )
    )
    residuals = list(db.scalars(select(TraceResidual).where(TraceResidual.analytical_run_id == run.id)))
    account_ids = {str(item.from_account_id) for item in flows} | {
        str(item.to_account_id) for item in flows if item.to_account_id
    }
    account_ids |= {str(item.account_id) for item in residuals}
    accounts = _accounts(db, account_ids)
    source_rows, _subjects = _load(db, run.case_id)
    by_source = {row.id: row for row in source_rows}
    flow_rows = []
    for item in flows:
        previous = [
            prior
            for prior in flows
            if prior.layer_to == item.layer_to - 1 and str(prior.to_account_id) == str(item.from_account_id)
        ]
        left = by_source.get(str(previous[0].source_transaction_id)) if len(previous) == 1 else None
        right = by_source.get(str(item.source_transaction_id))
        flow_rows.append(
            {
                "from_account_masked": _mask(accounts.get(str(item.from_account_id))),
                "to_account_masked": _mask(accounts.get(str(item.to_account_id)))
                if item.to_account_id
                else None,
                "from_account_id": str(item.from_account_id),
                "to_account_id": str(item.to_account_id) if item.to_account_id else None,
                "amount": f"{Decimal(str(item.amount)):.4f}",
                "currency": str(item.currency).strip(),
                "layer_to": item.layer_to,
                "assertion_kind": item.assertion_kind,
                "method_name": item.method_name,
                "method_version": item.method_version,
                "exit_kind": item.exit_kind,
                "source_transaction_id": str(item.source_transaction_id),
                "booking_date": right.booking_date.isoformat() if right else None,
                "booking_time": right.booking_time.isoformat() if right and right.booking_time else None,
                "hours_after_previous": _gap(left, right),
                "reference": right.reference if right else None,
            }
        )
    layers: dict[int, set[str]] = {}
    for flow_row in flow_rows:
        layer = flow_row["layer_to"]
        target = flow_row["to_account_masked"] or flow_row["exit_kind"]
        if isinstance(layer, int) and isinstance(target, str):
            layers.setdefault(layer, set()).add(target)
    origins = sorted(
        {
            str(row["from_account_masked"])
            for row in flow_rows
            if row["layer_to"] == 1 and row["from_account_masked"]
        }
    )
    finding = db.scalar(
        select(Finding).where(Finding.analytical_run_id == run.id, Finding.finding_kind == "trace")
    )
    return {
        "id": str(run.id),
        "job_id": str(job_id) if job_id else None,
        "status": run.status,
        "error_code": run.error_code,
        "method_version": run.method_version,
        "max_layer": run.parameters.get("max_layer"),
        "currency": run.parameters.get("currency"),
        "output_hash": run.output_hash,
        "input_hash": run.input_hash,
        "flows": flow_rows,
        "residuals": [
            {
                "account_masked": _mask(accounts.get(str(item.account_id))),
                "account_id": str(item.account_id),
                "amount": f"{Decimal(str(item.amount)):.4f}",
                "currency": str(item.currency).strip(),
                "reason": item.reason,
            }
            for item in residuals
        ],
        "path_summary": {
            "origin_accounts_masked": origins,
            "accounts_by_layer": [
                {"layer": layer, "accounts_masked": sorted(accounts)}
                for layer, accounts in sorted(layers.items())
            ],
            "holding_accounts_masked": sorted(
                {_mask(accounts.get(str(item.account_id))) or "****" for item in residuals}
            ),
            "note": "Layers are fifo.v1 allocations, not proof the same funds moved through each account.",
        },
        "limitations": finding.limitations if finding else "The run did not publish flows.",
        "data_classification": case.data_classification if (case := db.get(Case, run.case_id)) else None,
    }


def get_trace(db: Session, principal: Principal, trace_id: uuid.UUID) -> dict[str, object]:
    run = db.get(AnalyticalRun, trace_id)
    if run is None or run.run_kind != "trace":
        raise Problem(404, "not-found", "Not available", "This trace is not available.")
    _require_read(db, principal, run.case_id)
    return trace_body(db, run)


def run_indicators(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    window_start: date,
    window_end: date,
    fan_in_min: int,
    fan_out_min: int,
    pass_through_ratio: Decimal,
    pass_through_dwell_hours: Decimal,
    amount_floor: Decimal,
    currency: str,
    request_id: str | None,
) -> dict[str, object]:
    case = _require_analysis(db, principal, case_id, request_id, "indicator.run")
    if window_end < window_start:
        raise Problem(422, "invalid", "Invalid window", "The window end is before the start.")
    rows, _subjects = _load(db, case_id)
    parameters: dict[str, object] = {
        "amount_floor": f"{amount_floor.quantize(FOUR):.4f}",
        "currency": currency,
        "fan_in_min": fan_in_min,
        "fan_out_min": fan_out_min,
        "pass_through_dwell_hours": str(pass_through_dwell_hours),
        "pass_through_ratio": str(pass_through_ratio),
        "window_end": window_end.isoformat(),
        "window_start": window_start.isoformat(),
    }
    result = detect(
        rows,
        currency=currency,
        window_start=window_start,
        window_end=window_end,
        fan_in_min=fan_in_min,
        fan_out_min=fan_out_min,
        pass_through_ratio=pass_through_ratio,
        pass_through_dwell_hours=pass_through_dwell_hours,
        amount_floor=amount_floor,
    )
    run = AnalyticalRun(
        case_id=case.id,
        run_kind="indicators",
        method_name="indicators",
        method_version=INDICATOR_VERSION,
        parameters=parameters,
        input_hash=_input_hash(rows, parameters),
        output_hash=result.output_hash,
        status="succeeded",
        requested_by=principal.id,
    )
    db.add(run)
    db.flush()
    accounts = _accounts(db, {hit.account_id for hit in result.hits})
    support_ids = [tx_id for hit in result.hits for tx_id in hit.support_transaction_ids]
    transactions = _transactions(db, support_ids)
    for hit in result.hits:
        db.add(
            AccountIndicator(
                analytical_run_id=run.id,
                case_id=case.id,
                account_id=uuid.UUID(hit.account_id),
                code=hit.code,
                window_start=window_start,
                window_end=window_end,
                threshold=parameters,
                support_transaction_ids=[uuid.UUID(item) for item in hit.support_transaction_ids],
                assertion_kind="inferred",
                method_name="indicators",
                method_version=INDICATOR_VERSION,
                limitations=hit.limitations,
            )
        )
        _finding(
            db,
            run,
            kind="indicator",
            summary=(
                f"{hit.code} rule matched on the account ending {_tail(accounts.get(hit.account_id))}. "
                f"Distinct verified counterparties: {hit.distinct_counterparties}. "
                "This is a rule match, not a finding of guilt."
            ),
            assertion_kind="inferred",
            limitations=hit.limitations,
            method_name="indicators",
            method_version=INDICATOR_VERSION,
            transactions=[transactions[item] for item in hit.support_transaction_ids if item in transactions],
        )
    if not result.hits:
        _finding(
            db,
            run,
            kind="indicator",
            summary="No indicator rule matched. This is not a finding that the activity is legitimate.",
            assertion_kind="inferred",
            limitations=result.limitations + " Thresholds are demonstration settings, not legal thresholds.",
            method_name="indicators",
            method_version=INDICATOR_VERSION,
            transactions=[],
        )
    job = _job(db, case.id, "indicators", run)
    append_audit(
        db,
        action="indicator.run",
        outcome="success",
        object_kind="analytical_run",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(run.id),
        request_id=request_id,
        detail={"method_version": INDICATOR_VERSION, "hit_count": len(result.hits), "currency": currency},
    )
    return {
        "id": str(run.id),
        "job_id": str(job.id),
        "status": "succeeded",
        "items": _indicator_items(db, run),
    }


def _indicator_items(db: Session, run: AnalyticalRun) -> list[dict[str, object]]:
    rows = list(db.scalars(select(AccountIndicator).where(AccountIndicator.analytical_run_id == run.id)))
    accounts = _accounts(db, {str(row.account_id) for row in rows})
    return [
        {
            "code": row.code,
            "account_masked": _mask(accounts.get(str(row.account_id))),
            "account_id": str(row.account_id),
            "assertion_kind": row.assertion_kind,
            "method_version": row.method_version,
            "support_transaction_ids": [str(item) for item in row.support_transaction_ids],
            "limitations": row.limitations,
            "window_start": row.window_start.isoformat(),
            "window_end": row.window_end.isoformat(),
        }
        for row in rows
    ]


def list_indicators(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    _require_read(db, principal, case_id)
    run = db.scalar(
        select(AnalyticalRun)
        .where(
            AnalyticalRun.case_id == case_id,
            AnalyticalRun.run_kind == "indicators",
            AnalyticalRun.status == "succeeded",
        )
        .order_by(AnalyticalRun.created_at.desc())
    )
    if run is None:
        return {"items": [], "run_id": None}
    return {"items": _indicator_items(db, run), "run_id": str(run.id), "parameters": run.parameters}


def run_walk(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    start_account_id: uuid.UUID,
    direction: str,
    max_layer: int,
    currency: str,
    window_start: date,
    window_end: date,
    amount_min: str | None,
    amount_max: str | None,
    request_id: str | None,
) -> dict[str, object]:
    case = _require_analysis(db, principal, case_id, request_id, "statement_walk.run")
    if direction not in {"forward", "backward"}:
        raise Problem(422, "invalid", "Invalid direction", "Direction must be forward or backward.")
    if window_end < window_start:
        raise Problem(422, "invalid", "Invalid window", "The window end is before the start.")
    rows, subjects = _load(db, case_id)
    if str(start_account_id) not in subjects and str(start_account_id) not in {
        row.counterparty_account_id for row in rows
    }:
        raise Problem(404, "not-found", "Not available", "This account is not available in the case.")
    floor = _decimal(amount_min, "amount_min") if amount_min else None
    ceiling = _decimal(amount_max, "amount_max") if amount_max else None
    parameters: dict[str, object] = {
        "amount_max": str(ceiling) if ceiling is not None else None,
        "amount_min": str(floor) if floor is not None else None,
        "currency": currency,
        "direction": direction,
        "max_layer": max_layer,
        "start_account_id": str(start_account_id),
        "window_end": window_end.isoformat(),
        "window_start": window_start.isoformat(),
    }
    result = walk_statements(
        rows,
        start_account_id=str(start_account_id),
        direction=direction,
        max_layer=max_layer,
        currency=currency,
        window_start=window_start,
        window_end=window_end,
        amount_min=floor,
        amount_max=ceiling,
    )
    by_id = {row.id: row for row in rows}
    paths: list[dict[str, object]] = []
    support: list[Transaction] = []
    transactions = _transactions(
        db,
        [hop.transaction_id for path in result.paths for hop in path.hops],
    )
    for path in result.paths:
        hops = []
        previous: LedgerRow | None = None
        for hop in path.hops:
            current = by_id.get(hop.transaction_id)
            hops.append(
                {
                    "transaction_id": hop.transaction_id,
                    "from_account_id": hop.from_account_id,
                    "to_account_id": hop.to_account_id,
                    "amount": f"{hop.amount:.4f}",
                    "currency": currency,
                    "booking_date": hop.booking_date.isoformat() if hop.booking_date else None,
                    "booking_time": hop.booking_time.isoformat() if hop.booking_time else None,
                    "hours_after_previous": _gap(previous, current),
                }
            )
            previous = current
            if hop.transaction_id in transactions:
                support.append(transactions[hop.transaction_id])
        paths.append({"stop_reason": path.stop_reason, "hops": hops})
    output: dict[str, object] = {
        "truncated": result.truncated,
        "limitations": result.limitations,
        "paths": paths,
    }
    run = AnalyticalRun(
        case_id=case.id,
        run_kind="statement_walk",
        method_name="statement_walk",
        method_version=WALK_VERSION,
        parameters=parameters,
        input_hash=_input_hash(rows, parameters),
        output_hash=result.output_hash,
        output=output,
        status="succeeded",
        requested_by=principal.id,
    )
    db.add(run)
    db.flush()
    _finding(
        db,
        run,
        kind="statement_walk",
        summary=(
            f"Observed {direction} statement sequence at depth {max_layer}. "
            "This is not a FIFO allocation and not a finding of guilt."
        ),
        assertion_kind="hypothesis",
        limitations=result.limitations,
        method_name="statement_walk",
        method_version=WALK_VERSION,
        transactions=support,
    )
    job = _job(db, case.id, "statement_walk", run)
    append_audit(
        db,
        action="statement_walk.run",
        outcome="success",
        object_kind="analytical_run",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(run.id),
        request_id=request_id,
        detail={"method_version": WALK_VERSION, "direction": direction, "path_count": len(paths)},
    )
    return walk_body(db, run, job.id)


def walk_body(db: Session, run: AnalyticalRun, job_id: uuid.UUID | None = None) -> dict[str, object]:
    output = dict(run.output or {})
    paths = output.get("paths")
    masked_paths: list[dict[str, object]] = []
    if isinstance(paths, list):
        identifiers: set[str] = set()
        for path in paths:
            if isinstance(path, dict):
                hops = path.get("hops")
                if isinstance(hops, list):
                    for hop in hops:
                        if isinstance(hop, dict):
                            identifiers.add(str(hop.get("from_account_id")))
                            identifiers.add(str(hop.get("to_account_id")))
        accounts = _accounts(db, {item for item in identifiers if item and item != "None"})
        for path in paths:
            if not isinstance(path, dict):
                continue
            hops_out = []
            hops = path.get("hops")
            if isinstance(hops, list):
                for hop in hops:
                    if not isinstance(hop, dict):
                        continue
                    item = dict(hop)
                    item["from_account_masked"] = _mask(accounts.get(str(hop.get("from_account_id"))))
                    item["to_account_masked"] = _mask(accounts.get(str(hop.get("to_account_id"))))
                    hops_out.append(item)
            masked_paths.append({"stop_reason": path.get("stop_reason"), "hops": hops_out})
    return {
        "id": str(run.id),
        "job_id": str(job_id) if job_id else None,
        "status": run.status,
        "method_version": run.method_version,
        "direction": run.parameters.get("direction"),
        "max_layer": run.parameters.get("max_layer"),
        "truncated": output.get("truncated", False),
        "limitations": output.get("limitations"),
        "paths": masked_paths,
        "output_hash": run.output_hash,
    }


def get_walk(db: Session, principal: Principal, walk_id: uuid.UUID) -> dict[str, object]:
    run = db.get(AnalyticalRun, walk_id)
    if run is None or run.run_kind != "statement_walk":
        raise Problem(404, "not-found", "Not available", "This walk is not available.")
    _require_read(db, principal, run.case_id)
    return walk_body(db, run)


def list_findings(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    _require_read(db, principal, case_id)
    rows = list(
        db.scalars(
            select(Finding).where(Finding.case_id == case_id).order_by(Finding.created_at.desc()).limit(100)
        )
    )
    return {"items": [_finding_body(db, row) for row in rows]}


def get_finding(db: Session, principal: Principal, finding_id: uuid.UUID) -> dict[str, object]:
    row = db.get(Finding, finding_id)
    if row is None:
        raise Problem(404, "not-found", "Not available", "This finding is not available.")
    _require_read(db, principal, row.case_id)
    return _finding_body(db, row)


def _finding_body(db: Session, row: Finding) -> dict[str, object]:
    supports = list(db.scalars(select(FindingSupport).where(FindingSupport.finding_id == row.id)))
    evidence_ids = [item.evidence_id for item in supports]
    evidence = (
        list(db.scalars(select(EvidenceRecord).where(EvidenceRecord.id.in_(evidence_ids))))
        if evidence_ids
        else []
    )
    return {
        "id": str(row.id),
        "analytical_run_id": str(row.analytical_run_id),
        "finding_kind": row.finding_kind,
        "summary": row.summary,
        "assertion_kind": row.assertion_kind,
        "limitations": row.limitations,
        "method_name": row.method_name,
        "method_version": row.method_version,
        "evidence_ids": [str(item.id) for item in evidence],
        "support_transaction_ids": [str(item.object_id) for item in evidence if item.kind == "transaction"],
    }


def list_runs(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    _require_read(db, principal, case_id)
    rows = list(
        db.scalars(
            select(AnalyticalRun)
            .where(AnalyticalRun.case_id == case_id)
            .order_by(AnalyticalRun.created_at.desc())
            .limit(50)
        )
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "run_kind": row.run_kind,
                "method_name": row.method_name,
                "method_version": row.method_version,
                "status": row.status,
                "error_code": row.error_code,
                "input_hash": row.input_hash,
                "output_hash": row.output_hash,
                "parameters": row.parameters,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


def activity(
    db: Session, principal: Principal, case_id: uuid.UUID, currency: str | None
) -> dict[str, object]:
    case = _require_read(db, principal, case_id)
    rows, _subjects = _load(db, case_id)
    metrics = summarise(rows, currency.upper() if currency else None)
    accounts = _accounts(db, {item.account_id for item in metrics})
    return {
        "data_classification": case.data_classification,
        "comparison": "Amounts are not converted across currencies.",
        "items": [
            {
                "account_masked": _mask(accounts.get(item.account_id)),
                "account_id": item.account_id,
                "currency": item.currency,
                "incoming_count": item.incoming_count,
                "outgoing_count": item.outgoing_count,
                "incoming_amount": f"{item.incoming_amount:.4f}",
                "outgoing_amount": f"{item.outgoing_amount:.4f}",
                "unique_counterparties": item.unique_counterparties,
                "average_amount": f"{item.average_amount:.4f}" if item.average_amount is not None else None,
                "median_amount": f"{item.median_amount:.4f}" if item.median_amount is not None else None,
                "maximum_amount": f"{item.maximum_amount:.4f}" if item.maximum_amount is not None else None,
                "period_start": item.period_start.isoformat(),
                "period_end": item.period_end.isoformat(),
                "row_count": item.row_count,
                "date_only_count": item.date_only_count,
                "coverage": item.coverage,
            }
            for item in metrics
        ],
    }


def overview(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    case = _require_read(db, principal, case_id)
    count = int(
        db.scalar(select(func.count()).select_from(Transaction).where(Transaction.case_id == case_id)) or 0
    )
    body = activity(db, principal, case_id, None)
    raw_items = body["items"]
    items = raw_items if isinstance(raw_items, list) else []
    latest_trace = db.scalar(
        select(AnalyticalRun)
        .where(AnalyticalRun.case_id == case_id, AnalyticalRun.run_kind == "trace")
        .order_by(AnalyticalRun.created_at.desc())
    )
    indicators = list_indicators(db, principal, case_id)
    indicator_rows = indicators["items"]
    codes: list[str] = []
    if isinstance(indicator_rows, list):
        codes = [str(item["code"]) for item in indicator_rows if isinstance(item, dict) and "code" in item]
    return {
        "data_classification": case.data_classification,
        "transaction_count": count,
        "currencies": sorted({str(item["currency"]) for item in items if isinstance(item, dict)}),
        "activity": items,
        "latest_trace_status": latest_trace.status if latest_trace else None,
        "latest_trace_id": str(latest_trace.id) if latest_trace else None,
        "indicator_codes": codes,
        "coverage": "Figures are counts of stored rows. A missing statement is not stored as zero activity.",
    }


def parse_amount(raw: str) -> Decimal:
    return _decimal(raw, "amount")
