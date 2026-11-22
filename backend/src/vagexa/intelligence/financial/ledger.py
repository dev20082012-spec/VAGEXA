"""Rows the analytical methods read. They are not a second store."""

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal


@dataclass(frozen=True)
class LedgerRow:
    id: str
    account_id: str
    direction: str
    amount: Decimal
    currency: str
    booking_date: date
    booking_time: time | None
    line_number: int
    counterparty_account_id: str | None
    counterparty_resolution: str
    reference: str | None
    rail: str
    time_precision: str


def sort_key(row: LedgerRow) -> tuple[object, ...]:
    """booking_date, booking_time nulls last, line_number, id. ADR 0010."""
    return (
        row.booking_date,
        row.booking_time is None,
        row.booking_time or time.min,
        row.line_number,
        row.id,
    )
