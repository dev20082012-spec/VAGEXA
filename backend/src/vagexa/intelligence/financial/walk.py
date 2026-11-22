"""Observed statement sequences. Not an allocation and not a cycle label."""

import hashlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from vagexa.intelligence.financial.indicators import VerifiedEdge, verified_edges
from vagexa.intelligence.financial.ledger import LedgerRow

METHOD_VERSION = "statement_walk.v1"
MAX_PATHS = 25
LIMITATIONS = (
    "Observed statement sequence only. Not a FIFO allocation and not proof that the same funds "
    "moved through every account. Narration-derived links were excluded. A return to an earlier "
    "account stops that path. It is not a CYCLE finding."
)


@dataclass(frozen=True)
class Hop:
    transaction_id: str
    from_account_id: str
    to_account_id: str
    amount: Decimal
    booking_date: date
    booking_time: datetime | None


@dataclass(frozen=True)
class ObservedPath:
    hops: list[Hop]
    stop_reason: str


@dataclass
class WalkResult:
    paths: list[ObservedPath] = field(default_factory=list)
    truncated: bool = False
    limitations: str = LIMITATIONS
    output_hash: str | None = None


def _hop(edge: VerifiedEdge, forward: bool) -> Hop:
    when = edge.debit_time if forward or edge.credit_time is None else edge.credit_time
    booked = edge.debit_date if forward or edge.credit_date is None else edge.credit_date
    transaction_id = edge.debit_id if forward and edge.debit_id else (edge.credit_id or edge.debit_id or "")
    if not forward and edge.credit_id:
        transaction_id = edge.credit_id
    return Hop(
        transaction_id,
        edge.source_id,
        edge.dest_id,
        edge.amount,
        booked or date.min,
        when,
    )


def walk_statements(
    rows: list[LedgerRow],
    *,
    start_account_id: str,
    direction: str,
    max_layer: int,
    currency: str,
    window_start: date,
    window_end: date,
    amount_min: Decimal | None,
    amount_max: Decimal | None,
) -> WalkResult:
    forward = direction == "forward"
    edges = verified_edges(rows, currency=currency, window_start=window_start, window_end=window_end)
    chosen = [
        edge
        for edge in edges
        if (amount_min is None or edge.amount >= amount_min)
        and (amount_max is None or edge.amount <= amount_max)
    ]
    outgoing: dict[str, list[VerifiedEdge]] = defaultdict(list)
    incoming: dict[str, list[VerifiedEdge]] = defaultdict(list)
    for edge in chosen:
        outgoing[edge.source_id].append(edge)
        incoming[edge.dest_id].append(edge)
    for group in outgoing.values():
        group.sort(key=lambda edge: (edge.debit_date or date.min, edge.debit_id or ""))
    for group in incoming.values():
        group.sort(key=lambda edge: (edge.credit_date or edge.debit_date or date.min, edge.credit_id or ""))

    paths: list[ObservedPath] = []
    seen: set[tuple[str, ...]] = set()
    queue: deque[tuple[str, list[Hop]]] = deque([(start_account_id, [])])
    expansions = 0
    truncated = False
    while queue:
        account_id, hops = queue.popleft()
        expansions += 1
        if expansions > 1000:
            truncated = True
            break
        if len(hops) >= max_layer:
            key = tuple(hop.transaction_id for hop in hops)
            if key not in seen:
                seen.add(key)
                paths.append(ObservedPath(hops, "horizon"))
            if len(paths) >= MAX_PATHS:
                truncated = True
                break
            continue
        nxt = outgoing.get(account_id, []) if forward else incoming.get(account_id, [])
        extended = False
        accounts = (
            {start_account_id} | {hop.to_account_id for hop in hops} | {hop.from_account_id for hop in hops}
        )
        used = {hop.transaction_id for hop in hops}
        for edge in nxt:
            hop = _hop(edge, forward)
            if hop.transaction_id in used:
                continue
            destination = hop.to_account_id if forward else hop.from_account_id
            extended = True
            if destination in accounts:
                stopped = ObservedPath([*hops, hop], "returned_to_earlier_account")
                key = tuple(item.transaction_id for item in stopped.hops)
                if key not in seen:
                    seen.add(key)
                    paths.append(stopped)
                continue
            queue.append((destination, [*hops, hop]))
        if not extended and hops:
            key = tuple(hop.transaction_id for hop in hops)
            if key not in seen:
                seen.add(key)
                paths.append(ObservedPath(hops, "no_further_record"))
        if len(paths) >= MAX_PATHS:
            truncated = True
            break
    if not paths:
        paths.append(ObservedPath([], "no_further_record"))
    payload = [
        {
            "hops": [
                {
                    "amount": f"{hop.amount:.4f}",
                    "from_account_id": hop.from_account_id,
                    "to_account_id": hop.to_account_id,
                    "transaction_id": hop.transaction_id,
                }
                for hop in path.hops
            ],
            "stop_reason": path.stop_reason,
        }
        for path in paths
    ]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return WalkResult(paths=paths[:MAX_PATHS], truncated=truncated, output_hash=digest)
