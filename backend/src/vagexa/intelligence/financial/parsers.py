"""CSV and JSON adapters. Both emit canonical statement legs."""

import csv
import json
import re
from decimal import Decimal, InvalidOperation
from io import StringIO

from vagexa.intelligence.financial.canonical import (
    POSTED_STATUSES,
    RAILS,
    CanonicalLeg,
    ParseOutput,
    RowIssue,
    normalise_account,
    normalise_ifsc,
    normalise_vpa,
    parse_amount,
    parse_timestamp,
)

IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
CANONICAL_REQUIRED = {"line_number", "booking_date", "direction", "amount", "currency", "rail"}
TRANSFER_REQUIRED = {"source_account", "destination_account", "amount", "currency"}


def decode_text(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", payload, 0, 1, "not utf-8")


def parse_dataset(
    payload: bytes,
    *,
    subject_account: str | None,
    subject_ifsc: str | None,
    subject_vpa: str | None,
) -> ParseOutput:
    if not payload.strip():
        return ParseOutput(
            parser_name="none",
            file_issues=[
                RowIssue(
                    0,
                    "file",
                    "empty_file",
                    "The file has no records.",
                    "Upload a CSV or JSON dataset.",
                )
            ],
        )
    try:
        text = decode_text(payload)
    except UnicodeDecodeError:
        return ParseOutput(
            parser_name="none",
            file_issues=[
                RowIssue(
                    0,
                    "file",
                    "invalid_encoding",
                    "The file is not UTF-8 text.",
                    "Save the file as UTF-8.",
                )
            ],
        )
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return _parse_json(text, subject_account, subject_ifsc, subject_vpa)
    return _parse_csv(text, subject_account, subject_ifsc, subject_vpa)


def _parse_csv(
    text: str,
    subject_account: str | None,
    subject_ifsc: str | None,
    subject_vpa: str | None,
) -> ParseOutput:
    try:
        reader = csv.DictReader(StringIO(text))
        fieldnames = [name.strip() for name in (reader.fieldnames or []) if name]
        rows = list(reader)
    except csv.Error as exc:
        return ParseOutput(
            parser_name="csv",
            file_issues=[RowIssue(0, "file", "malformed_csv", str(exc), "Repair the CSV quoting.")],
        )
    return _rows_from_maps(rows, fieldnames, "csv", subject_account, subject_ifsc, subject_vpa)


def _parse_json(
    text: str,
    subject_account: str | None,
    subject_ifsc: str | None,
    subject_vpa: str | None,
) -> ParseOutput:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        return ParseOutput(
            parser_name="json",
            file_issues=[RowIssue(0, "file", "malformed_json", exc.msg, "Send a JSON array of records.")],
        )
    if isinstance(loaded, dict) and isinstance(loaded.get("records"), list):
        records = loaded["records"]
    elif isinstance(loaded, list):
        records = loaded
    else:
        return ParseOutput(
            parser_name="json",
            file_issues=[
                RowIssue(
                    0,
                    "file",
                    "malformed_json",
                    "JSON must be an array of records.",
                    "Use a list of objects.",
                )
            ],
        )
    maps: list[dict[str, str | None]] = []
    issues: list[RowIssue] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            issues.append(
                RowIssue(
                    index,
                    "record",
                    "malformed_row",
                    "Each JSON record must be an object.",
                    "Replace this item with an object.",
                )
            )
            continue
        maps.append({str(key): "" if value is None else str(value) for key, value in record.items()})
    fieldnames: list[str] = []
    for item in maps:
        for key in item:
            if key not in fieldnames:
                fieldnames.append(key)
    output = _rows_from_maps(maps, fieldnames, "json", subject_account, subject_ifsc, subject_vpa)
    output.row_issues = issues + output.row_issues
    return output


def _rows_from_maps(
    rows: list[dict[str, str | None]],
    fieldnames: list[str],
    kind: str,
    subject_account: str | None,
    subject_ifsc: str | None,
    subject_vpa: str | None,
) -> ParseOutput:
    names = set(fieldnames)
    transfer = TRANSFER_REQUIRED <= names
    canonical = CANONICAL_REQUIRED <= names
    if not transfer and not canonical:
        return ParseOutput(
            parser_name=kind,
            file_issues=[
                RowIssue(
                    0,
                    "file",
                    "missing_columns",
                    "The header is neither a statement nor a transfer dataset.",
                    "Include statement columns or source_account, destination_account, amount, and currency.",
                )
            ],
        )
    if not transfer and not (normalise_account(subject_account) or normalise_vpa(subject_vpa)):
        return ParseOutput(
            parser_name=f"{kind}_statement",
            file_issues=[
                RowIssue(
                    0,
                    "subject_account",
                    "missing_field",
                    "A statement file needs the subject account.",
                    "Provide the account number and IFSC, or a VPA.",
                )
            ],
        )
    known = (
        CANONICAL_REQUIRED
        | TRANSFER_REQUIRED
        | {
            "booking_time",
            "narration",
            "counterparty_account",
            "counterparty_ifsc",
            "counterparty_vpa",
            "reference",
            "balance_after",
            "source_transaction_id",
            "line_number",
            "source_ifsc",
            "destination_ifsc",
            "timestamp",
            "transaction_type",
            "payment_reference",
            "status",
        }
    )
    unexpected = [name for name in fieldnames if name not in known]
    output = ParseOutput(
        parser_name=f"{kind}_transfer" if transfer else f"{kind}_statement",
        unexpected_columns=unexpected,
    )
    if not rows:
        output.file_issues.append(
            RowIssue(
                0,
                "file",
                "empty_file",
                "The file has headers but no records.",
                "Add at least one record.",
            )
        )
        return output
    for index, row in enumerate(rows, start=1):
        cleaned = {
            key: (value or "").strip() if isinstance(value, str) else "" for key, value in row.items() if key
        }
        line_number = index
        if not transfer and cleaned.get("line_number", "").isdigit():
            line_number = int(cleaned["line_number"])
        leg, issues = (
            _transfer_leg(line_number, cleaned)
            if transfer
            else _statement_leg(line_number, cleaned, subject_account, subject_ifsc, subject_vpa)
        )
        output.row_issues.extend(issues)
        if leg is not None and not any(issue.blocks_insert for issue in issues):
            output.legs.append(leg)
    return output


def _statement_leg(
    line_number: int,
    row: dict[str, str],
    subject_account: str | None,
    subject_ifsc: str | None,
    subject_vpa: str | None,
) -> tuple[CanonicalLeg | None, list[RowIssue]]:
    issues: list[RowIssue] = []
    direction = row.get("direction", "").lower()
    if direction not in {"debit", "credit"}:
        issues.append(
            RowIssue(
                line_number,
                "direction",
                "invalid_field",
                "Direction must be debit or credit.",
                "Use debit or credit.",
            )
        )
    rail = row.get("rail", "unknown").lower() or "unknown"
    if rail not in RAILS:
        issues.append(
            RowIssue(
                line_number,
                "rail",
                "invalid_field",
                "That rail is not recognised.",
                "Use upi, imps, neft, rtgs, cash, cheque, card, internal, or unknown.",
            )
        )
        rail = "unknown"
    amount = _amount_issue(line_number, row.get("amount", ""), issues)
    currency = _currency_issue(line_number, row.get("currency", ""), issues)
    booking = _time_issue(line_number, row.get("booking_date", ""), row.get("booking_time", ""), issues)
    balance = None
    if row.get("balance_after"):
        try:
            balance = (
                parse_amount(row["balance_after"])
                if Decimal(row["balance_after"]) > 0
                else Decimal(row["balance_after"])
            )
        except (InvalidOperation, ValueError):
            issues.append(
                RowIssue(
                    line_number,
                    "balance_after",
                    "invalid_amount",
                    "Balance is not a decimal.",
                    "Use a decimal with at most four places.",
                )
            )
    if any(issue.blocks_insert for issue in issues) or amount is None or currency is None or booking is None:
        return None, issues
    booked, clock, precision = booking
    return CanonicalLeg(
        line_number=line_number,
        subject_account=normalise_account(subject_account) or "",
        subject_ifsc=normalise_ifsc(subject_ifsc),
        subject_vpa=normalise_vpa(subject_vpa),
        direction=direction,
        amount=amount,
        currency=currency,
        booking_date=booked,
        booking_time=clock,
        time_precision=precision,
        rail=rail,
        narration=row.get("narration", ""),
        counterparty_account=normalise_account(row.get("counterparty_account")),
        counterparty_ifsc=normalise_ifsc(row.get("counterparty_ifsc")),
        counterparty_vpa=normalise_vpa(row.get("counterparty_vpa")),
        reference=row.get("reference") or None,
        balance_after=balance,
        source_transaction_id=row.get("source_transaction_id") or None,
        original=row,
    ), issues


def _transfer_leg(line_number: int, row: dict[str, str]) -> tuple[CanonicalLeg | None, list[RowIssue]]:
    issues: list[RowIssue] = []
    status = (row.get("status") or "posted").lower()
    if status not in POSTED_STATUSES:
        issues.append(
            RowIssue(
                line_number,
                "status",
                "unsupported_status",
                f"Status {status} is not a posted ledger leg.",
                "Use posted or completed. Pending and failed rows are kept as errors, not as transactions.",
            )
        )
    source = normalise_account(row.get("source_account"))
    if not source:
        issues.append(
            RowIssue(
                line_number,
                "source_account",
                "missing_field",
                "Source account is required.",
                "Provide the sending account number.",
            )
        )
    destination = normalise_account(row.get("destination_account"))
    if not destination:
        issues.append(
            RowIssue(
                line_number,
                "destination_account",
                "missing_field",
                "Destination account is required.",
                "Provide the receiving account number.",
            )
        )
    source_ifsc = normalise_ifsc(row.get("source_ifsc"))
    dest_ifsc = normalise_ifsc(row.get("destination_ifsc"))
    if source_ifsc and not IFSC_RE.match(source_ifsc):
        issues.append(
            RowIssue(
                line_number,
                "source_ifsc",
                "invalid_account",
                "The source IFSC shape is invalid.",
                "Use 4 letters, a 0, then 6 letters or digits.",
            )
        )
    if dest_ifsc and not IFSC_RE.match(dest_ifsc):
        issues.append(
            RowIssue(
                line_number,
                "destination_ifsc",
                "invalid_account",
                "The destination IFSC shape is invalid.",
                "Use 4 letters, a 0, then 6 letters or digits.",
            )
        )
    if source and not source_ifsc:
        issues.append(
            RowIssue(
                line_number,
                "source_ifsc",
                "invalid_account",
                "A bank account needs an IFSC.",
                "Add the source IFSC.",
            )
        )
    if destination and not dest_ifsc:
        issues.append(
            RowIssue(
                line_number,
                "destination_ifsc",
                "invalid_account",
                "A bank account needs an IFSC.",
                "Add the destination IFSC.",
            )
        )
    amount = _amount_issue(line_number, row.get("amount", ""), issues)
    currency = _currency_issue(line_number, row.get("currency", ""), issues)
    when = row.get("timestamp") or row.get("booking_date") or ""
    booking = _time_issue(line_number, when, "", issues)
    rail = (row.get("transaction_type") or "unknown").lower()
    if rail not in RAILS:
        rail = "unknown"
    if (
        any(issue.blocks_insert for issue in issues)
        or not source
        or not destination
        or amount is None
        or currency is None
        or booking is None
    ):
        return None, issues
    booked, clock, precision = booking
    return CanonicalLeg(
        line_number=line_number,
        subject_account=source,
        subject_ifsc=source_ifsc,
        subject_vpa=None,
        direction="debit",
        amount=amount,
        currency=currency,
        booking_date=booked,
        booking_time=clock,
        time_precision=precision,
        rail=rail,
        narration="",
        counterparty_account=destination,
        counterparty_ifsc=dest_ifsc,
        counterparty_vpa=None,
        reference=row.get("payment_reference") or None,
        balance_after=None,
        source_transaction_id=row.get("source_transaction_id") or None,
        original=row,
    ), issues


def _amount_issue(line_number: int, raw: str, issues: list[RowIssue]) -> Decimal | None:
    try:
        return parse_amount(raw)
    except (InvalidOperation, ValueError):
        issues.append(
            RowIssue(
                line_number,
                "amount",
                "invalid_amount",
                "Amount must be a positive decimal with at most four places.",
                "Remove currency symbols and use a decimal such as 1000.50.",
            )
        )
        return None


def _currency_issue(line_number: int, raw: str, issues: list[RowIssue]) -> str | None:
    currency = raw.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        issues.append(
            RowIssue(
                line_number,
                "currency",
                "invalid_currency",
                "Currency must be a three-letter ISO code.",
                "Use INR or USD.",
            )
        )
        return None
    return currency


def _time_issue(line_number: int, raw: str, extra_time: str, issues: list[RowIssue]) -> tuple | None:
    text = raw.strip()
    if extra_time.strip() and " " not in text and "T" not in text:
        text = f"{text} {extra_time.strip()}"
    if not text:
        issues.append(
            RowIssue(
                line_number,
                "timestamp",
                "invalid_timestamp",
                "A booking date or timestamp is required.",
                "Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.",
            )
        )
        return None
    try:
        return parse_timestamp(text)
    except ValueError:
        issues.append(
            RowIssue(
                line_number,
                "timestamp",
                "invalid_timestamp",
                "That timestamp format is not recognised.",
                "Use YYYY-MM-DD, DD/MM/YYYY, or an ISO date-time.",
            )
        )
        return None
