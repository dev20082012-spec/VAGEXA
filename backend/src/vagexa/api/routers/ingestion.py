import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, File, Form, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.models import Account, IngestionIssue, Job, Statement, Transaction
from vagexa.api.deps import DB, request_id_of, require_principal
from vagexa.api.errors import Problem
from vagexa.application import case_service, ingestion_service
from vagexa.application.auth_service import Principal
from vagexa.config import Settings

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


def _mask(number: str | None) -> str | None:
    if not number:
        return None
    tail = number[-4:]
    return f"****{tail}"


def _job_body(job: Job) -> dict[str, object]:
    payload = job.payload or {}
    return {
        "id": str(job.id),
        "case_id": str(job.case_id),
        "status": job.status,
        "error_code": job.error_code,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "summary": {
            "original_filename": payload.get("original_filename"),
            "byte_size": payload.get("byte_size"),
            "sha256": payload.get("sha256"),
            "parser_name": payload.get("parser_name"),
            "parser_version": payload.get("parser_version"),
            "unexpected_columns": payload.get("unexpected_columns", []),
            "records_total": payload.get("records_total", 0),
            "records_valid": payload.get("records_valid", 0),
            "records_invalid": payload.get("records_invalid", 0),
            "records_duplicate": payload.get("records_duplicate", 0),
            "records_potential_duplicate": payload.get("records_potential_duplicate", 0),
            "idempotent_replay": payload.get("idempotent_replay", False),
            "data_classification": payload.get("data_classification"),
        },
    }


@router.post("/cases/{case_id}/statements", status_code=201)
async def upload_statement(
    case_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    subject_account: str | None = Form(None),
    subject_ifsc: str | None = Form(None),
    subject_vpa: str | None = Form(None),
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    settings: Settings = request.app.state.settings
    payload = await file.read(settings.upload_max_bytes + 1)
    job = ingestion_service.ingest_file(
        db,
        settings,
        principal,
        case_id=case_id,
        filename=file.filename or "upload",
        payload=payload,
        subject_account=subject_account,
        subject_ifsc=subject_ifsc,
        subject_vpa=subject_vpa,
        request_id=request_id_of(request),
    )
    body = _job_body(job)
    if job.payload.get("idempotent_replay"):
        return body
    return body


@router.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return _job_body(ingestion_service.job_for_case(db, principal, job_id))


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    return _job_body(ingestion_service.cancel_job(db, principal, job_id, request_id_of(request)))


@router.get("/jobs/{job_id}/issues")
def job_issues(job_id: uuid.UUID, request: Request, db: Session = DB) -> dict[str, object]:
    principal = require_principal(request, db)
    job = ingestion_service.job_for_case(db, principal, job_id)
    rows = db.scalars(
        select(IngestionIssue).where(IngestionIssue.job_id == job.id).order_by(IngestionIssue.line_number)
    )
    return {
        "items": [
            {
                "line_number": row.line_number,
                "field_name": row.field_name,
                "category": row.category,
                "message": row.message,
                "suggestion": row.suggestion,
                "blocks_insert": row.blocks_insert,
            }
            for row in rows
        ]
    }


def _readable(db: Session, principal: Principal, case_id: uuid.UUID) -> None:
    try:
        case_service.get_case(db, principal, case_id, None)
    except Problem:
        raise


@router.get("/cases/{case_id}/transactions")
def list_transactions(
    case_id: uuid.UUID,
    request: Request,
    db: Session = DB,
    direction: str | None = None,
    currency: str | None = None,
    rail: str | None = None,
    booking_date_from: date | None = None,
    booking_date_to: date | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    account_id: uuid.UUID | None = None,
    source_transaction_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    principal = require_principal(request, db)
    _readable(db, principal, case_id)
    if offset < 0 or offset > 10_000:
        raise Problem(422, "invalid", "Invalid page", "The page offset is outside the allowed range.")
    limit = min(max(limit, 1), 100)
    query = select(Transaction).where(Transaction.case_id == case_id)
    if account_id:
        query = query.join(Statement, Statement.id == Transaction.statement_id).where(
            Statement.account_id == account_id
        )
    if direction:
        query = query.where(Transaction.direction == direction)
    if currency:
        query = query.where(Transaction.currency == currency.upper())
    if rail:
        query = query.where(Transaction.rail == rail)
    if booking_date_from:
        query = query.where(Transaction.booking_date >= booking_date_from)
    if booking_date_to:
        query = query.where(Transaction.booking_date <= booking_date_to)
    if source_transaction_id:
        query = query.where(Transaction.source_transaction_id == source_transaction_id)
    for raw, column, label in (
        (amount_min, Transaction.amount, "amount_min"),
        (amount_max, Transaction.amount, "amount_max"),
    ):
        if raw is None:
            continue
        try:
            bound = Decimal(raw)
        except InvalidOperation as exc:
            raise Problem(422, "invalid", "Invalid amount", "Amounts must be decimals.") from exc
        query = query.where(column >= bound) if label == "amount_min" else query.where(column <= bound)
    window = list(
        db.scalars(
            query.order_by(
                Transaction.booking_date, Transaction.booking_time.nulls_last(), Transaction.line_number
            )
            .offset(offset)
            .limit(limit + 1)
        )
    )
    extra = len(window) > limit
    rows = window[:limit]
    statements = (
        {
            row.id: row.account_id
            for row in db.scalars(
                select(Statement).where(Statement.id.in_({item.statement_id for item in rows}))
            )
        }
        if rows
        else {}
    )
    ids = {item.counterparty_account_id for item in rows if item.counterparty_account_id}
    ids |= set(statements.values())
    accounts = {}
    if ids:
        accounts = {row.id: row for row in db.scalars(select(Account).where(Account.id.in_(ids)))}
    return {
        "items": [
            {
                "id": str(row.id),
                "account_id": str(statements[row.statement_id]) if row.statement_id in statements else None,
                "account_masked": _mask(accounts[statements[row.statement_id]].account_number_norm)
                if statements.get(row.statement_id) in accounts
                else None,
                "counterparty_account_id": str(row.counterparty_account_id)
                if row.counterparty_account_id
                else None,
                "line_number": row.line_number,
                "booking_date": row.booking_date.isoformat(),
                "booking_time": row.booking_time.isoformat() if row.booking_time else None,
                "time_precision": row.time_precision,
                "direction": row.direction,
                "amount": f"{row.amount:.4f}",
                "currency": row.currency.strip(),
                "rail": row.rail,
                "counterparty_masked": _mask(accounts[row.counterparty_account_id].account_number_norm)
                if row.counterparty_account_id in accounts
                else None,
                "counterparty_resolution": row.counterparty_resolution,
                "reference_raw": row.reference_raw,
                "source_transaction_id": row.source_transaction_id,
                "data_classification": row.data_classification,
            }
            for row in rows
        ],
        "next_cursor": str(offset + limit) if extra else None,
    }


@router.get("/cases/{case_id}/transactions/{transaction_id}")
def transaction_detail(
    case_id: uuid.UUID,
    transaction_id: uuid.UUID,
    request: Request,
    db: Session = DB,
) -> dict[str, object]:
    principal = require_principal(request, db)
    _readable(db, principal, case_id)
    row = db.get(Transaction, transaction_id)
    if row is None or row.case_id != case_id:
        raise Problem(404, "not-found", "Not available", "This transaction is not available.")
    count = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.case_id == case_id))
    return {
        "id": str(row.id),
        "amount": f"{row.amount:.4f}",
        "currency": row.currency.strip(),
        "direction": row.direction,
        "booking_date": row.booking_date.isoformat(),
        "booking_time": row.booking_time.isoformat() if row.booking_time else None,
        "rail": row.rail,
        "reference_raw": row.reference_raw,
        "source_transaction_id": row.source_transaction_id,
        "original_record": row.original_record,
        "data_classification": row.data_classification,
        "provenance_id": str(row.provenance_id),
        "line_number": row.line_number,
        "case_transaction_count": count,
    }
