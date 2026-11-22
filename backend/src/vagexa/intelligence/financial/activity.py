"""Account activity from statement rows. No baseline and no cross-currency total."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from vagexa.intelligence.financial.ledger import LedgerRow

FOUR = Decimal("0.0001")
COVERAGE = (
    "Metrics count this account's own statement rows in one currency. "
    "The other side of a transfer is not added again. "
    "Amounts are not converted across currencies. "
    "No earlier period is stored separately, so a dormant-to-active comparison is not made."
)


@dataclass(frozen=True)
class AccountActivity:
    account_id: str
    currency: str
    incoming_count: int
    outgoing_count: int
    incoming_amount: Decimal
    outgoing_amount: Decimal
    unique_counterparties: int
    average_amount: Decimal | None
    median_amount: Decimal | None
    maximum_amount: Decimal | None
    period_start: date
    period_end: date
    row_count: int
    date_only_count: int
    coverage: str = COVERAGE


def _median(amounts: list[Decimal]) -> Decimal:
    ordered = sorted(amounts)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid].quantize(FOUR)
    return ((ordered[mid - 1] + ordered[mid]) / Decimal(2)).quantize(FOUR, rounding=ROUND_HALF_UP)


def summarise(rows: list[LedgerRow], currency: str | None = None) -> list[AccountActivity]:
    grouped: dict[tuple[str, str], list[LedgerRow]] = defaultdict(list)
    for row in rows:
        if currency and row.currency != currency:
            continue
        grouped[(row.account_id, row.currency)].append(row)
    results: list[AccountActivity] = []
    for (account_id, row_currency), group in sorted(grouped.items()):
        incoming = [row for row in group if row.direction == "credit"]
        outgoing = [row for row in group if row.direction == "debit"]
        amounts = [row.amount for row in group]
        counterparties = {
            row.counterparty_account_id
            for row in group
            if row.counterparty_resolution == "structured_field" and row.counterparty_account_id
        }
        total = sum(amounts, Decimal("0"))
        results.append(
            AccountActivity(
                account_id=account_id,
                currency=row_currency,
                incoming_count=len(incoming),
                outgoing_count=len(outgoing),
                incoming_amount=sum((row.amount for row in incoming), Decimal("0")).quantize(FOUR),
                outgoing_amount=sum((row.amount for row in outgoing), Decimal("0")).quantize(FOUR),
                unique_counterparties=len(counterparties),
                average_amount=(total / Decimal(len(amounts))).quantize(FOUR, rounding=ROUND_HALF_UP),
                median_amount=_median(amounts),
                maximum_amount=max(amounts).quantize(FOUR),
                period_start=min(row.booking_date for row in group),
                period_end=max(row.booking_date for row in group),
                row_count=len(group),
                date_only_count=sum(1 for row in group if row.time_precision == "date"),
            )
        )
    return results
