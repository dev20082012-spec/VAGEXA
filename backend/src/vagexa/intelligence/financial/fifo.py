"""fifo.v1. Oldest attributed lot is spent first. This does not prove the same funds continued."""

import hashlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal

from vagexa.intelligence.financial.ledger import LedgerRow, sort_key

METHOD_VERSION = "fifo.v1"
MAX_ROWS = 10_000
MAX_FLOWS = 20_000
TOLERANCE = Decimal("0.01")
FOUR = Decimal("0.0001")


@dataclass
class Lot:
    amount: Decimal
    complaint_id: str | None
    arrival_layer: int


@dataclass(frozen=True)
class Flow:
    from_account_id: str
    to_account_id: str | None
    exit_kind: str | None
    source_transaction_id: str
    amount: Decimal
    currency: str
    layer_to: int
    assertion_kind: str
    method_name: str
    complaint_id: str | None


@dataclass(frozen=True)
class Residual:
    account_id: str
    complaint_id: str | None
    amount: Decimal
    currency: str
    reason: str


@dataclass(frozen=True)
class Seed:
    transaction_id: str
    complaint_id: str | None = None


@dataclass
class TraceResult:
    status: str
    error_code: str | None
    flows: list[Flow] = field(default_factory=list)
    residuals: list[Residual] = field(default_factory=list)
    limitations: str = ""
    output_hash: str | None = None
    date_only: bool = False


def _money(amount: Decimal) -> str:
    return f"{amount.quantize(FOUR):.4f}"


def _limitations(max_layer: int, date_only: bool) -> str:
    parts = [
        f"Horizon {max_layer}.",
        "Amounts are inside the supplied statements under fifo.v1.",
        "outside_horizon is not an attributed beneficiary.",
        "A flow is an allocation under this policy, not proof the same funds continued.",
        "A no_onward_record residual repeats the flow into an account with no statement.",
    ]
    if date_only:
        parts.append("Date-only rows follow file order, not clock order.")
    return " ".join(parts)


def _hash(flows: list[Flow], residuals: list[Residual]) -> str:
    payload = {
        "flows": [
            {
                "amount": _money(item.amount),
                "assertion_kind": item.assertion_kind,
                "complaint_id": item.complaint_id,
                "currency": item.currency,
                "exit_kind": item.exit_kind,
                "from_account_id": item.from_account_id,
                "layer_to": item.layer_to,
                "method_name": item.method_name,
                "source_transaction_id": item.source_transaction_id,
                "to_account_id": item.to_account_id,
            }
            for item in sorted(
                flows,
                key=lambda item: (
                    item.layer_to,
                    item.from_account_id,
                    item.to_account_id or "",
                    item.source_transaction_id,
                    _money(item.amount),
                ),
            )
        ],
        "residuals": [
            {
                "account_id": item.account_id,
                "amount": _money(item.amount),
                "complaint_id": item.complaint_id,
                "currency": item.currency,
                "reason": item.reason,
            }
            for item in sorted(
                residuals,
                key=lambda item: (item.account_id, item.reason, _money(item.amount), item.complaint_id or ""),
            )
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _net_remainders(rows: list[LedgerRow]) -> dict[str, Decimal]:
    remaining = {row.id: row.amount for row in rows}
    grouped: dict[str, list[LedgerRow]] = defaultdict(list)
    for row in rows:
        grouped[row.account_id].append(row)
    for group in grouped.values():
        open_debits: list[LedgerRow] = []
        for row in sorted(group, key=sort_key):
            if row.direction == "debit":
                open_debits.append(row)
                continue
            if not row.reference:
                continue
            for debit in open_debits:
                if (
                    debit.reference
                    and debit.reference == row.reference
                    and debit.currency == row.currency
                    and remaining[row.id] <= remaining[debit.id]
                    and remaining[row.id] > 0
                ):
                    remaining[debit.id] -= remaining[row.id]
                    remaining[row.id] = Decimal("0")
                    break
    return remaining


def _mirrors(rows: list[LedgerRow]) -> dict[str, str]:
    """Credit id to the debit id of the same referenced transfer. Amount alone does not match."""
    debits = [
        row for row in rows if row.direction == "debit" and row.reference and row.counterparty_account_id
    ]
    credits = [
        row for row in rows if row.direction == "credit" and row.reference and row.counterparty_account_id
    ]
    paired: dict[str, str] = {}
    used: set[str] = set()
    for debit in sorted(debits, key=sort_key):
        for credit in sorted(credits, key=sort_key):
            if credit.id in used:
                continue
            if (
                credit.reference == debit.reference
                and credit.currency == debit.currency
                and credit.amount == debit.amount
                and credit.account_id == debit.counterparty_account_id
                and credit.counterparty_account_id == debit.account_id
            ):
                paired[credit.id] = debit.id
                used.add(credit.id)
                break
    return paired


def _classify(row: LedgerRow, mirrored: bool) -> tuple[str, str, str | None, str | None]:
    if row.rail == "cash":
        return "verified", "cash_exit", None, "cash"
    if row.counterparty_resolution == "unresolved" or not row.counterparty_account_id:
        return "verified", "unresolved_exit", None, "unresolved"
    kind = "verified"
    method = "reference_join" if mirrored else "structured_counterparty"
    if row.counterparty_resolution == "narration_pattern":
        kind = "inferred"
        method = "narration_extractor"
    return kind, method, row.counterparty_account_id, None


def _conserves(
    flows: list[Flow],
    introductions: list[tuple[str, str, str | None, Decimal]],
) -> bool:
    inflow: dict[tuple[str, str, str | None], Decimal] = defaultdict(lambda: Decimal("0"))
    outflow: dict[tuple[str, str, str | None], Decimal] = defaultdict(lambda: Decimal("0"))
    for account_id, currency, complaint_id, amount in introductions:
        inflow[(account_id, currency, complaint_id)] += amount
    for item in flows:
        outflow[(item.from_account_id, item.currency, item.complaint_id)] += item.amount
        if item.to_account_id:
            inflow[(item.to_account_id, item.currency, item.complaint_id)] += item.amount
    keys = set(inflow) | set(outflow)
    return all(outflow[key] <= inflow[key] + TOLERANCE for key in keys)


def trace(
    rows: list[LedgerRow],
    seeds: list[Seed],
    *,
    max_layer: int,
    currency: str,
    statement_account_ids: set[str],
    fault_extra_outflow: Decimal | None = None,
) -> TraceResult:
    date_only = any(row.time_precision == "date" for row in rows)
    limitations = _limitations(max_layer, date_only)
    if len(rows) > MAX_ROWS:
        return TraceResult("failed", "input_too_large", limitations=limitations, date_only=date_only)
    if not 1 <= max_layer <= 5:
        return TraceResult("failed", "layer_out_of_range", limitations=limitations, date_only=date_only)
    by_id = {row.id: row for row in rows}
    seed_ids = {seed.transaction_id: seed for seed in seeds}
    if any(seed.transaction_id not in by_id for seed in seeds):
        return TraceResult("failed", "seed_not_found", limitations=limitations, date_only=date_only)
    if any(by_id[seed.transaction_id].currency != currency for seed in seeds):
        return TraceResult("failed", "currency_mismatch", limitations=limitations, date_only=date_only)

    remaining = _net_remainders(rows)
    credit_to_debit = _mirrors(rows)
    mirrored_debits = set(credit_to_debit.values())
    queues: dict[tuple[str, str], deque[Lot]] = defaultdict(deque)
    flows: list[Flow] = []
    residuals: list[Residual] = []
    introductions: list[tuple[str, str, str | None, Decimal]] = []

    def emit(
        row: LedgerRow,
        amount: Decimal,
        layer: int,
        complaint_id: str | None,
        *,
        arrival_if_held: int | None,
    ) -> None:
        if len(flows) >= MAX_FLOWS:
            raise RuntimeError("result_too_large")
        assertion, method, destination, exit_kind = _classify(row, row.id in mirrored_debits)
        if exit_kind is not None:
            destination = None
        flows.append(
            Flow(
                from_account_id=row.account_id,
                to_account_id=destination,
                exit_kind=exit_kind,
                source_transaction_id=row.id,
                amount=amount.quantize(FOUR),
                currency=currency,
                layer_to=layer,
                assertion_kind=assertion,
                method_name=method,
                complaint_id=complaint_id,
            )
        )
        if destination is None or layer > max_layer:
            return
        if destination not in statement_account_ids:
            residuals.append(
                Residual(destination, complaint_id, amount.quantize(FOUR), currency, "no_onward_record")
            )
            return
        queues[(destination, currency)].append(
            Lot(
                amount.quantize(FOUR), complaint_id, arrival_if_held if arrival_if_held is not None else layer
            )
        )

    def spend(row: LedgerRow, need: Decimal) -> None:
        queue = queues[(row.account_id, currency)]
        left = need
        while left > 0 and queue:
            lot = queue[0]
            take = min(left, lot.amount)
            layer = lot.arrival_layer + 1
            if layer > max_layer:
                residuals.append(
                    Residual(
                        row.account_id, lot.complaint_id, take.quantize(FOUR), currency, "outside_horizon"
                    )
                )
            else:
                emit(row, take, layer, lot.complaint_id, arrival_if_held=layer)
            lot.amount -= take
            left -= take
            if lot.amount <= 0:
                queue.popleft()

    try:
        for row in sorted(rows, key=sort_key):
            if row.currency != currency:
                continue
            amount = remaining[row.id]
            if amount <= 0:
                continue
            mirrored_debit = credit_to_debit.get(row.id)
            if mirrored_debit is not None and (row.id not in seed_ids or mirrored_debit in seed_ids):
                continue
            seed = seed_ids.get(row.id)
            if seed is not None and row.direction == "debit":
                introductions.append((row.account_id, currency, seed.complaint_id, amount.quantize(FOUR)))
                emit(row, amount, 1, seed.complaint_id, arrival_if_held=1)
                continue
            if seed is not None and row.direction == "credit":
                held = amount.quantize(FOUR)
                introductions.append((row.account_id, currency, seed.complaint_id, held))
                queues[(row.account_id, currency)].append(Lot(held, seed.complaint_id, 0))
                continue
            if row.direction == "debit":
                spend(row, amount)
    except RuntimeError:
        return TraceResult("failed", "result_too_large", limitations=limitations, date_only=date_only)

    if fault_extra_outflow is not None and seeds:
        source = by_id[seeds[0].transaction_id]
        flows.append(
            Flow(
                from_account_id=source.account_id,
                to_account_id=None,
                exit_kind="unresolved",
                source_transaction_id=source.id,
                amount=fault_extra_outflow.quantize(FOUR),
                currency=currency,
                layer_to=1,
                assertion_kind="verified",
                method_name="unresolved_exit",
                complaint_id=seeds[0].complaint_id,
            )
        )
    if not _conserves(flows, introductions):
        return TraceResult("failed", "conservation", limitations=limitations, date_only=date_only)
    return TraceResult(
        status="succeeded",
        error_code=None,
        flows=flows,
        residuals=residuals,
        limitations=limitations,
        output_hash=_hash(flows, residuals),
        date_only=date_only,
    )
