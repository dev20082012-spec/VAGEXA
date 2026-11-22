"""Canonical statement legs. Amounts stay Decimal. Original text is kept."""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

RAILS = {"upi", "imps", "neft", "rtgs", "cash", "cheque", "card", "internal", "unknown"}
POSTED_STATUSES = {"posted", "completed"}
PARSER_VERSION = "ingest.v1"


@dataclass
class RowIssue:
    line_number: int
    field_name: str
    category: str
    message: str
    suggestion: str
    blocks_insert: bool = True


@dataclass
class CanonicalLeg:
    line_number: int
    subject_account: str
    subject_ifsc: str | None
    subject_vpa: str | None
    direction: str
    amount: Decimal
    currency: str
    booking_date: date
    booking_time: time | None
    time_precision: str
    rail: str
    narration: str
    counterparty_account: str | None
    counterparty_ifsc: str | None
    counterparty_vpa: str | None
    reference: str | None
    balance_after: Decimal | None
    source_transaction_id: str | None
    original: dict[str, str]
    content_key: str = ""

    def __post_init__(self) -> None:
        self.content_key = "|".join(
            [
                self.subject_account,
                self.subject_ifsc or "",
                self.direction,
                format(self.amount, "f"),
                self.currency,
                self.booking_date.isoformat(),
                self.booking_time.isoformat() if self.booking_time else "",
                self.counterparty_account or "",
                self.counterparty_ifsc or "",
                self.reference or "",
                self.source_transaction_id or "",
            ]
        )


@dataclass
class ParseOutput:
    parser_name: str
    unexpected_columns: list[str] = field(default_factory=list)
    file_issues: list[RowIssue] = field(default_factory=list)
    legs: list[CanonicalLeg] = field(default_factory=list)
    row_issues: list[RowIssue] = field(default_factory=list)


def parse_amount(raw: str) -> Decimal:
    text = raw.strip()
    if not text or any(char in text for char in "eE"):
        raise InvalidOperation
    amount = Decimal(text)
    exponent = amount.as_tuple().exponent
    if not isinstance(exponent, int) or exponent < -4 or amount <= 0:
        raise InvalidOperation
    return amount


def normalise_ifsc(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    return "".join(raw.split()).upper()


def normalise_account(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    return "".join(raw.split())


def normalise_vpa(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    return raw.strip().lower()


def parse_timestamp(raw: str) -> tuple[date, time | None, str]:
    text = raw.strip()
    for pattern, precision in (
        ("%Y-%m-%d", "date"),
        ("%d/%m/%Y", "date"),
        ("%Y-%m-%d %H:%M:%S", "time"),
        ("%Y-%m-%dT%H:%M:%S", "time"),
    ):
        try:
            parsed = datetime.strptime(text, pattern)
        except ValueError:
            continue
        clock = parsed.time() if precision == "time" else None
        return parsed.date(), clock, precision
    if text.endswith("Z"):
        try:
            zulu = datetime.strptime(text[:-1], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            zulu = None
        if zulu is not None:
            return zulu.date(), zulu.time(), "time"
    if "T" in text and ("+" in text[10:] or text.count("-") > 2):
        try:
            aware = datetime.fromisoformat(text)
        except ValueError:
            aware = None
        if aware is not None:
            return aware.date(), aware.time().replace(microsecond=0), "time"
    raise ValueError(text)
