"""indicators.v1. Rule matches on verified structured-field transfers. Not a probability."""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from vagexa.intelligence.financial.ledger import LedgerRow, sort_key

METHOD_VERSION = "indicators.v1"
EXCLUSION = "Verified edges only. Narration-derived links were excluded. This is a rule match."
FOUR = Decimal("0.0001")


@dataclass(frozen=True)
class VerifiedEdge:
    source_id: str
    dest_id: str
    debit_id: str | None
    credit_id: str | None
    amount: Decimal
    currency: str
    debit_date: date | None
    credit_date: date | None
    debit_time: datetime | None
    credit_time: datetime | None
    debit_precision: str | None
    credit_precision: str | None


@dataclass(frozen=True)
class IndicatorHit:
    code: str
    account_id: str
    support_transaction_ids: list[str]
    limitations: str
    distinct_counterparties: int
    amount: Decimal


@dataclass
class IndicatorResult:
    hits: list[IndicatorHit] = field(default_factory=list)
    limitations: str = EXCLUSION
    output_hash: str | None = None


def _stamp(row: LedgerRow) -> datetime | None:
    if row.time_precision != "time" or row.booking_time is None:
        return None
    return datetime.combine(row.booking_date, row.booking_time)


def verified_edges(
    rows: list[LedgerRow],
    *,
    currency: str,
    window_start: date,
    window_end: date,
) -> list[VerifiedEdge]:
    scoped = [
        row
        for row in rows
        if row.currency == currency
        and row.counterparty_resolution == "structured_field"
        and row.counterparty_account_id
        and window_start <= row.booking_date <= window_end
    ]
    debits = [row for row in scoped if row.direction == "debit"]
    credits = [row for row in scoped if row.direction == "credit"]
    used: set[str] = set()
    edges: list[VerifiedEdge] = []
    for debit in sorted(debits, key=sort_key):
        match = None
        for credit in sorted(credits, key=sort_key):
            if credit.id in used or not credit.reference or not debit.reference:
                continue
            if (
                credit.reference == debit.reference
                and credit.amount == debit.amount
                and credit.account_id == debit.counterparty_account_id
                and credit.counterparty_account_id == debit.account_id
            ):
                match = credit
                break
        if match is not None:
            used.add(match.id)
            edges.append(
                VerifiedEdge(
                    debit.account_id,
                    debit.counterparty_account_id or "",
                    debit.id,
                    match.id,
                    debit.amount,
                    currency,
                    debit.booking_date,
                    match.booking_date,
                    _stamp(debit),
                    _stamp(match),
                    debit.time_precision,
                    match.time_precision,
                )
            )
        else:
            edges.append(
                VerifiedEdge(
                    debit.account_id,
                    debit.counterparty_account_id or "",
                    debit.id,
                    None,
                    debit.amount,
                    currency,
                    debit.booking_date,
                    None,
                    _stamp(debit),
                    None,
                    debit.time_precision,
                    None,
                )
            )
    for credit in sorted(credits, key=sort_key):
        if credit.id in used:
            continue
        edges.append(
            VerifiedEdge(
                credit.counterparty_account_id or "",
                credit.account_id,
                None,
                credit.id,
                credit.amount,
                currency,
                None,
                credit.booking_date,
                None,
                _stamp(credit),
                None,
                credit.time_precision,
            )
        )
    return edges


def _support(edge: VerifiedEdge, prefer_credit: bool) -> str:
    if prefer_credit and edge.credit_id:
        return edge.credit_id
    if edge.debit_id:
        return edge.debit_id
    return edge.credit_id or ""


def _clocks(edges: list[VerifiedEdge], inbound: bool) -> list[datetime] | None:
    stamps: list[datetime] = []
    for edge in edges:
        precision = edge.credit_precision if inbound else edge.debit_precision
        stamp = edge.credit_time if inbound else edge.debit_time
        if edge.credit_id and edge.debit_id:
            if edge.debit_precision != "time" or edge.credit_precision != "time":
                return None
            if edge.debit_time is None or edge.credit_time is None:
                return None
            stamp = edge.credit_time if inbound else edge.debit_time
        elif precision != "time" or stamp is None:
            return None
        stamps.append(stamp)
    return stamps


def _dwell_ok(
    in_edges: list[VerifiedEdge], out_edges: list[VerifiedEdge], dwell_hours: Decimal
) -> tuple[bool, str]:
    incoming = _clocks(in_edges, True)
    outgoing = _clocks(out_edges, False)
    if incoming is None or outgoing is None:
        return True, " Dwell was not applied because at least one supporting row is date-only."
    start = min(incoming)
    end = max(outgoing)
    delta = end - start
    if delta < timedelta(0):
        return False, ""
    actual = (
        Decimal(delta.days) * Decimal(86400)
        + Decimal(delta.seconds)
        + (Decimal(delta.microseconds) / Decimal(1_000_000))
    )
    if actual > dwell_hours * Decimal(3600):
        return False, ""
    return True, " Dwell was applied using the supplied clocks."


def _hash(hits: list[IndicatorHit]) -> str:
    payload = [
        {
            "account_id": hit.account_id,
            "amount": f"{hit.amount.quantize(FOUR):.4f}",
            "code": hit.code,
            "distinct_counterparties": hit.distinct_counterparties,
            "support_transaction_ids": hit.support_transaction_ids,
        }
        for hit in hits
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def detect(
    rows: list[LedgerRow],
    *,
    currency: str,
    window_start: date,
    window_end: date,
    fan_in_min: int,
    fan_out_min: int,
    pass_through_ratio: Decimal,
    pass_through_dwell_hours: Decimal,
    amount_floor: Decimal,
) -> IndicatorResult:
    edges = verified_edges(rows, currency=currency, window_start=window_start, window_end=window_end)
    incoming: dict[str, list[VerifiedEdge]] = defaultdict(list)
    outgoing: dict[str, list[VerifiedEdge]] = defaultdict(list)
    for edge in edges:
        incoming[edge.dest_id].append(edge)
        outgoing[edge.source_id].append(edge)
    accounts = sorted(set(incoming) | set(outgoing))
    hits: list[IndicatorHit] = []
    for account_id in accounts:
        inn = incoming.get(account_id, [])
        out = outgoing.get(account_id, [])
        sources = sorted({edge.source_id for edge in inn})
        if len(sources) >= fan_in_min:
            support = sorted({_support(edge, True) for edge in inn})
            note = (
                " Support ids are credit rows on this account."
                if all(edge.credit_id for edge in inn)
                else (" Support ids are debit rows that name this account as the structured counterparty.")
            )
            hits.append(
                IndicatorHit(
                    "FAN_IN",
                    account_id,
                    support,
                    EXCLUSION + note,
                    len(sources),
                    sum((edge.amount for edge in inn), Decimal("0")),
                )
            )
        destinations = sorted({edge.dest_id for edge in out})
        if len(destinations) >= fan_out_min:
            support = sorted({_support(edge, False) for edge in out})
            note = (
                " Support ids are debit rows on this account."
                if all(edge.debit_id for edge in out)
                else (" Support ids are credit rows that name this account as the structured counterparty.")
            )
            hits.append(
                IndicatorHit(
                    "FAN_OUT",
                    account_id,
                    support,
                    EXCLUSION + note,
                    len(destinations),
                    sum((edge.amount for edge in out), Decimal("0")),
                )
            )
        inflow = sum((edge.amount for edge in inn), Decimal("0"))
        outflow = sum((edge.amount for edge in out), Decimal("0"))
        if inflow > amount_floor and outflow > amount_floor and outflow / inflow >= pass_through_ratio:
            ok, dwell_note = _dwell_ok(inn, out, pass_through_dwell_hours)
            if ok:
                support = sorted(
                    {_support(edge, True) for edge in inn} | {_support(edge, False) for edge in out}
                )
                hits.append(
                    IndicatorHit(
                        "PASS_THROUGH",
                        account_id,
                        support,
                        EXCLUSION
                        + " Inflow and outflow are verified structured-field sums, not a FIFO allocation."
                        + dwell_note,
                        len(sources),
                        outflow,
                    )
                )
    return IndicatorResult(hits=hits, limitations=EXCLUSION, output_hash=_hash(hits))
