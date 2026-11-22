"""Store original bytes, then persist canonical legs. Invalid rows stay as issues."""

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import (
    Account,
    AccountObservation,
    Case,
    CaseAssignment,
    IngestionIssue,
    Job,
    ProvenanceRecord,
    SourceFile,
    Statement,
    Transaction,
)
from vagexa.api.errors import Problem
from vagexa.application.auth_service import Principal
from vagexa.config import Settings
from vagexa.domain.authorization import case_role_allows
from vagexa.intelligence.financial.canonical import PARSER_VERSION, CanonicalLeg, RowIssue
from vagexa.intelligence.financial.parsers import parse_dataset


def _require_mutate(db: Session, principal: Principal, case_id: uuid.UUID, request_id: str | None) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    if case is None or assignment is None or not case_role_allows(assignment.case_role, "cases.mutate"):
        append_audit(
            db,
            action="statement.upload",
            outcome="denied",
            object_kind="case",
            actor_id=principal.id,
            case_id=case.id if case and assignment else None,
            object_id=str(case_id),
            request_id=request_id,
        )
        if case is None or assignment is None:
            raise Problem(404, "not-found", "Not available", "This case is not available.")
        raise Problem(403, "forbidden", "Not allowed", "You cannot upload statements for this case.")
    return case


def _storage_path(settings: Settings, key: str) -> Path:
    root = Path(settings.storage_dir).resolve()
    path = (root / key).resolve()
    if root not in path.parents and path != root:
        raise Problem(422, "invalid", "Invalid storage key", "The file could not be stored.")
    return path


def _account(db: Session, number: str | None, ifsc: str | None, vpa: str | None) -> Account:
    if vpa:
        found = db.scalar(select(Account).where(Account.vpa_norm == vpa))
        if found:
            return found
        row = Account(kind="vpa", vpa_norm=vpa)
    else:
        found = db.scalar(
            select(Account).where(Account.account_number_norm == number, Account.ifsc_norm == ifsc)
        )
        if found:
            return found
        row = Account(kind="bank", account_number_norm=number, ifsc_norm=ifsc)
    db.add(row)
    db.flush()
    return row


def resolve_account(db: Session, number: str | None, ifsc: str | None, vpa: str | None) -> Account:
    """Exact instrument key. The same normalised number and IFSC, or the same VPA, is one row."""
    return _account(db, number, ifsc, vpa)


def ingest_file(
    db: Session,
    settings: Settings,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    filename: str,
    payload: bytes,
    subject_account: str | None,
    subject_ifsc: str | None,
    subject_vpa: str | None,
    request_id: str | None,
) -> Job:
    case = _require_mutate(db, principal, case_id, request_id)
    if len(payload) > settings.upload_max_bytes:
        raise Problem(413, "payload-too-large", "File too large", "The upload exceeds the size limit.")
    if not payload:
        raise Problem(422, "invalid", "Empty upload", "The file is empty.")
    digest = hashlib.sha256(payload).hexdigest()
    existing = db.scalar(select(SourceFile).where(SourceFile.case_id == case_id, SourceFile.sha256 == digest))
    if existing and existing.job_id:
        job = db.get(Job, existing.job_id)
        if job is not None:
            payload_copy = dict(job.payload)
            payload_copy["idempotent_replay"] = True
            job.payload = payload_copy
            return job
    safe_name = Path(filename).name or "upload"
    key = f"{case_id}/{uuid.uuid4().hex}"
    path = _storage_path(settings, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    now = datetime.now(UTC)
    provenance = ProvenanceRecord(
        data_classification=case.data_classification,
        source_system="upload",
        source_reference=digest,
        collected_at=now,
        collected_by=str(principal.id),
        method_name=PARSER_VERSION,
        raw_hash=digest,
    )
    db.add(provenance)
    db.flush()
    job = Job(
        kind="parse_statement",
        case_id=case_id,
        payload={"idempotent_replay": False},
        status="running",
        attempts=1,
        locked_at=now,
        locked_by="api",
    )
    db.add(job)
    db.flush()
    source = SourceFile(
        case_id=case_id,
        job_id=job.id,
        sha256=digest,
        byte_size=len(payload),
        original_filename=safe_name[:200],
        media_type="application/octet-stream",
        storage_key=key,
        status="stored",
        data_classification=case.data_classification,
        uploaded_by=principal.id,
        provenance_id=provenance.id,
    )
    db.add(source)
    db.flush()
    parsed = parse_dataset(
        payload,
        subject_account=subject_account,
        subject_ifsc=subject_ifsc,
        subject_vpa=subject_vpa,
    )
    issues = list(parsed.file_issues)
    inserted = 0
    duplicates = 0
    invalid = 0
    potential = 0
    seen_keys: set[str] = set()
    seen_source_ids: set[str] = set()
    statements: dict[tuple[str, str | None], Statement] = {}
    if not parsed.file_issues:
        for leg in parsed.legs:
            decision = _classify_duplicate(db, case_id, leg, seen_keys, seen_source_ids)
            if decision == "exact" or decision == "source_id":
                duplicates += 1
                issues.append(
                    RowIssue(
                        leg.line_number,
                        "source_transaction_id" if decision == "source_id" else "record",
                        "duplicate_source_id" if decision == "source_id" else "exact_duplicate",
                        "This record was not inserted again.",
                        "Keep the original row. A repeated upload of the same bytes is also ignored.",
                    )
                )
                continue
            if decision == "potential":
                potential += 1
                issues.append(
                    RowIssue(
                        leg.line_number,
                        "record",
                        "potential_duplicate",
                        "A similar posted leg already exists. This row was kept.",
                        "Compare the source identifiers. Similar amount and accounts are not merged.",
                        blocks_insert=False,
                    )
                )
            _insert_leg(db, case, source, provenance, parsed.parser_name, leg, statements)
            inserted += 1
            seen_keys.add(leg.content_key)
            if leg.source_transaction_id:
                seen_source_ids.add(leg.source_transaction_id)
        for issue in parsed.row_issues:
            if issue.blocks_insert:
                invalid += 1
            issues.append(issue)
    for issue in issues:
        db.add(
            IngestionIssue(
                job_id=job.id,
                case_id=case_id,
                line_number=issue.line_number,
                field_name=issue.field_name,
                category=issue.category,
                message=issue.message,
                suggestion=issue.suggestion,
                blocks_insert=issue.blocks_insert,
            )
        )
    file_failed = bool(parsed.file_issues)
    source.status = "rejected" if file_failed else "parsed"
    if file_failed:
        job.status = "failed"
        job.error_code = parsed.file_issues[0].category
    elif issues:
        job.status = "succeeded_with_errors"
    else:
        job.status = "succeeded"
    job.finished_at = datetime.now(UTC)
    job.payload = {
        "source_file_id": str(source.id),
        "sha256": digest,
        "original_filename": source.original_filename,
        "byte_size": len(payload),
        "parser_name": parsed.parser_name,
        "parser_version": PARSER_VERSION,
        "unexpected_columns": parsed.unexpected_columns,
        "records_total": inserted + invalid + duplicates,
        "records_valid": inserted,
        "records_invalid": invalid,
        "records_duplicate": duplicates,
        "records_potential_duplicate": potential,
        "idempotent_replay": False,
        "data_classification": case.data_classification,
    }
    append_audit(
        db,
        action="statement.upload",
        outcome="success" if job.status != "failed" else "failure",
        object_kind="source_file",
        actor_id=principal.id,
        case_id=case_id,
        object_id=str(source.id),
        request_id=request_id,
        detail={"sha256": digest, "status": job.status},
    )
    return job


def _classify_duplicate(
    db: Session,
    case_id: uuid.UUID,
    leg: CanonicalLeg,
    seen_keys: set[str],
    seen_source_ids: set[str],
) -> str | None:
    if leg.content_key in seen_keys:
        return "exact"
    if leg.source_transaction_id and leg.source_transaction_id in seen_source_ids:
        return "source_id"
    if leg.source_transaction_id:
        existing_id = db.scalar(
            select(Transaction.id).where(
                Transaction.case_id == case_id,
                Transaction.source_transaction_id == leg.source_transaction_id,
            )
        )
        if existing_id is not None:
            return "source_id"
    subject = db.scalar(
        select(Account.id).where(
            Account.account_number_norm == leg.subject_account,
            Account.ifsc_norm == leg.subject_ifsc,
        )
    )
    if subject is None or not leg.counterparty_account:
        return None
    similar = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .join(Statement, Statement.id == Transaction.statement_id)
        .join(Account, Account.id == Transaction.counterparty_account_id)
        .where(
            Transaction.case_id == case_id,
            Statement.account_id == subject,
            Account.account_number_norm == leg.counterparty_account,
            Transaction.amount == leg.amount,
            Transaction.currency == leg.currency,
            Transaction.booking_date == leg.booking_date,
            Transaction.source_transaction_id.is_distinct_from(leg.source_transaction_id),
        )
    )
    if similar:
        return "potential"
    return None


def _insert_leg(
    db: Session,
    case: Case,
    source: SourceFile,
    provenance: ProvenanceRecord,
    parser_name: str,
    leg: CanonicalLeg,
    statements: dict[tuple[str, str | None], Statement],
) -> None:
    subject = _account(db, leg.subject_account or None, leg.subject_ifsc, leg.subject_vpa)
    key = (leg.subject_account, leg.subject_ifsc)
    statement = statements.get(key)
    if statement is None:
        statement = Statement(
            case_id=case.id,
            source_file_id=source.id,
            account_id=subject.id,
            parser_name=parser_name,
            parser_version=PARSER_VERSION,
            currency=leg.currency,
            data_classification=case.data_classification,
            provenance_id=provenance.id,
        )
        db.add(statement)
        db.flush()
        statements[key] = statement
        db.add(
            AccountObservation(
                account_id=subject.id,
                case_id=case.id,
                statement_id=statement.id,
                account_number_raw=leg.original.get("source_account") or leg.original.get("subject_account"),
                data_classification=case.data_classification,
                provenance_id=provenance.id,
            )
        )
    counterparty_id = None
    resolution = "unresolved"
    if leg.counterparty_account and leg.counterparty_ifsc:
        counterparty_id = _account(db, leg.counterparty_account, leg.counterparty_ifsc, None).id
        resolution = "structured_field"
    elif leg.counterparty_vpa:
        counterparty_id = _account(db, None, None, leg.counterparty_vpa).id
        resolution = "structured_field"
    db.add(
        Transaction(
            statement_id=statement.id,
            case_id=case.id,
            line_number=leg.line_number,
            booking_date=leg.booking_date,
            booking_time=leg.booking_time,
            time_precision=leg.time_precision,
            direction=leg.direction,
            amount=leg.amount,
            currency=leg.currency,
            rail=leg.rail,
            narration_raw=leg.narration,
            counterparty_account_id=counterparty_id,
            counterparty_resolution=resolution,
            reference_raw=leg.reference,
            source_transaction_id=leg.source_transaction_id,
            original_record=leg.original,
            data_classification=case.data_classification,
            provenance_id=provenance.id,
        )
    )


def job_for_case(db: Session, principal: Principal, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise Problem(404, "not-found", "Not available", "This job is not available.")
    assignment = db.get(CaseAssignment, (job.case_id, principal.id))
    if assignment is None or not case_role_allows(assignment.case_role, "cases.read"):
        raise Problem(404, "not-found", "Not available", "This job is not available.")
    return job


def cancel_job(db: Session, principal: Principal, job_id: uuid.UUID, request_id: str | None) -> Job:
    job = job_for_case(db, principal, job_id)
    assignment = db.get(CaseAssignment, (job.case_id, principal.id))
    if assignment is None or not case_role_allows(assignment.case_role, "cases.mutate"):
        raise Problem(403, "forbidden", "Not allowed", "You cannot cancel this job.")
    if job.status != "queued":
        raise Problem(409, "conflict", "Job is not queued", "Only a queued job can be cancelled.")
    job.status = "cancelled"
    job.finished_at = datetime.now(UTC)
    append_audit(
        db,
        action="statement.upload",
        outcome="success",
        object_kind="job",
        actor_id=principal.id,
        case_id=job.case_id,
        object_id=str(job.id),
        request_id=request_id,
        detail={"status": "cancelled"},
    )
    return job
