"""correlate.v2. A shared key, an exact host in stored text, or a gateway record. Time alone creates nothing.

v2 adds the gateway rule. Rows written by v1 keep their stored version.
"""

import re
from dataclasses import dataclass

from vagexa.intelligence.digital.normalise import (
    OVERLAP_LIMITATION,
    IndicatorRejected,
    normalise_domain,
    normalise_ip,
)

METHOD_VERSION = "correlate.v2"
MAX_PROPOSALS = 500
GATEWAY = (
    "A payment-gateway record names this account as the settlement account for this merchant domain, "
    "and a statement row with the same reference, amount, and accounts exists. It does not identify "
    "who operates the domain or show that the account holder knew of the payment."
)
CONTAINMENT = (
    "The stored narration contains this exact host or address. "
    "Containment is not use, ownership, or a finding of guilt."
)
SAME_REFERENCE = (
    "Both rows cite the same reference as a structured field. This does not create an additional transfer."
)
_HOST = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


@dataclass(frozen=True)
class CorrTx:
    id: str
    account_id: str
    narration: str
    reference: str | None
    resolution: str
    direction: str = ""
    amount: str = ""
    currency: str = ""
    counterparty_account_id: str | None = None


@dataclass(frozen=True)
class CorrGateway:
    id: str
    payment_reference: str
    payer_account_id: str | None
    payee_account_id: str
    domain_id: str
    amount: str
    currency: str


@dataclass(frozen=True)
class CorrDomain:
    id: str
    name: str


@dataclass(frozen=True)
class CorrIp:
    id: str
    address: str


@dataclass(frozen=True)
class CorrDns:
    id: str
    domain_id: str
    ip_id: str


@dataclass(frozen=True)
class CorrHost:
    id: str
    ip_id: str | None
    provider_name: str | None


@dataclass(frozen=True)
class Proposal:
    pair_key: str
    rel_type: str
    from_kind: str
    from_id: str
    to_kind: str
    to_id: str
    assertion_kind: str
    limitation: str
    support: tuple[tuple[str, str], ...]
    explanation: str


def hosts_in_text(text: str) -> set[str]:
    found: set[str] = set()
    for match in _HOST.findall(text or ""):
        try:
            found.add(normalise_domain(match))
        except IndicatorRejected:
            continue
    return found


def addresses_in_text(text: str) -> set[str]:
    found: set[str] = set()
    for match in _IPV4.findall(text or ""):
        try:
            found.add(normalise_ip(match))
        except IndicatorRejected:
            continue
    return found


def correlate(
    transactions: list[CorrTx],
    domains: list[CorrDomain],
    addresses: list[CorrIp],
    dns: list[CorrDns],
    hosting: list[CorrHost],
    gateway: list[CorrGateway] | None = None,
) -> tuple[list[Proposal], bool]:
    proposals: list[Proposal] = []
    seen: set[str] = set()
    truncated = False

    def add(item: Proposal) -> None:
        nonlocal truncated
        if item.pair_key in seen:
            return
        if len(proposals) >= MAX_PROPOSALS:
            truncated = True
            return
        seen.add(item.pair_key)
        proposals.append(item)

    by_name = {domain.name: domain for domain in domains}
    by_address = {item.address: item for item in addresses}
    for tx in transactions:
        for name in hosts_in_text(tx.narration):
            domain = by_name.get(name)
            if domain is None:
                continue
            add(
                Proposal(
                    pair_key=f"mentioned_in:{tx.id}:{domain.id}",
                    rel_type="mentioned_in",
                    from_kind="account",
                    from_id=tx.account_id,
                    to_kind="domain",
                    to_id=domain.id,
                    assertion_kind="verified",
                    limitation=CONTAINMENT,
                    support=(("transaction", tx.id),),
                    explanation=CONTAINMENT,
                )
            )
        for address in addresses_in_text(tx.narration):
            ip = by_address.get(address)
            if ip is None:
                continue
            add(
                Proposal(
                    pair_key=f"mentioned_in:{tx.id}:{ip.id}",
                    rel_type="mentioned_in",
                    from_kind="account",
                    from_id=tx.account_id,
                    to_kind="ip",
                    to_id=ip.id,
                    assertion_kind="verified",
                    limitation=CONTAINMENT,
                    support=(("transaction", tx.id),),
                    explanation=CONTAINMENT,
                )
            )

    grouped: dict[str, list[CorrTx]] = {}
    for tx in transactions:
        if tx.resolution == "structured_field" and tx.reference:
            grouped.setdefault(tx.reference, []).append(tx)
    for reference, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: item.id)
        for left, right in zip(ordered, ordered[1:], strict=False):
            add(
                Proposal(
                    pair_key=f"same_payment:{reference}:{left.id}:{right.id}",
                    rel_type="same_payment",
                    from_kind="account",
                    from_id=left.account_id,
                    to_kind="account",
                    to_id=right.account_id,
                    assertion_kind="verified",
                    limitation=SAME_REFERENCE,
                    support=(("transaction", left.id), ("transaction", right.id)),
                    explanation=SAME_REFERENCE,
                )
            )

    by_ip: dict[str, list[str]] = {}
    dns_by_domain_ip: dict[tuple[str, str], list[str]] = {}
    for row in dns:
        by_ip.setdefault(row.ip_id, []).append(row.domain_id)
        dns_by_domain_ip.setdefault((row.domain_id, row.ip_id), []).append(row.id)
    for ip_id, domain_ids in by_ip.items():
        unique = sorted(set(domain_ids))
        for domain_left, domain_right in zip(unique, unique[1:], strict=False):
            left_ids = dns_by_domain_ip.get((domain_left, ip_id), [])
            right_ids = dns_by_domain_ip.get((domain_right, ip_id), [])
            support_ids = left_ids + right_ids
            add(
                Proposal(
                    pair_key=f"overlap:{ip_id}:{domain_left}:{domain_right}",
                    rel_type="infrastructure_overlap",
                    from_kind="domain",
                    from_id=domain_left,
                    to_kind="domain",
                    to_id=domain_right,
                    assertion_kind="verified",
                    limitation=OVERLAP_LIMITATION,
                    support=tuple(("dns_observation", item) for item in sorted(set(support_ids))),
                    explanation=OVERLAP_LIMITATION,
                )
            )

    by_provider: dict[str, list[CorrHost]] = {}
    for note in hosting:
        if note.provider_name and note.ip_id:
            by_provider.setdefault(note.provider_name.strip().lower(), []).append(note)
    for provider, notes in by_provider.items():
        address_ids = sorted({note.ip_id for note in notes if note.ip_id})
        for address_left, address_right in zip(address_ids, address_ids[1:], strict=False):
            support = tuple(
                ("hosting_observation", note.id)
                for note in notes
                if note.ip_id in {address_left, address_right}
            )
            add(
                Proposal(
                    pair_key=f"overlap-provider:{provider}:{address_left}:{address_right}",
                    rel_type="infrastructure_overlap",
                    from_kind="ip",
                    from_id=address_left,
                    to_kind="ip",
                    to_id=address_right,
                    assertion_kind="verified",
                    limitation=OVERLAP_LIMITATION,
                    support=support,
                    explanation=OVERLAP_LIMITATION,
                )
            )

    for record in gateway or []:
        legs = [tx for tx in transactions if _settles(tx, record)]
        if not legs:
            continue
        add(
            Proposal(
                pair_key=f"gateway:{record.id}:{record.domain_id}",
                rel_type="gateway_merchant",
                from_kind="account",
                from_id=record.payee_account_id,
                to_kind="domain",
                to_id=record.domain_id,
                assertion_kind="verified",
                limitation=GATEWAY,
                support=(("gateway_record", record.id),)
                + tuple(("transaction", tx.id) for tx in sorted(legs, key=lambda item: item.id)),
                explanation=GATEWAY,
            )
        )
    return proposals, truncated


def _settles(tx: CorrTx, record: CorrGateway) -> bool:
    """Same structured reference, amount, currency, and the payer-to-payee direction."""
    if tx.resolution != "structured_field" or tx.reference != record.payment_reference:
        return False
    if tx.amount != record.amount or tx.currency != record.currency:
        return False
    if tx.direction == "debit":
        payer_ok = record.payer_account_id is None or tx.account_id == record.payer_account_id
        return payer_ok and tx.counterparty_account_id == record.payee_account_id
    if tx.direction == "credit":
        payer_ok = record.payer_account_id is None or tx.counterparty_account_id == record.payer_account_id
        return payer_ok and tx.account_id == record.payee_account_id
    return False
