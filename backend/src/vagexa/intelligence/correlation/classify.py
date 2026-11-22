"""Display classification for stored relationships. The assertion kind is not changed here."""

from dataclasses import dataclass

DIRECTLY_SUPPORTED = "DIRECTLY_SUPPORTED"
CORROBORATED = "CORROBORATED"
INFERRED = "INFERRED"
HYPOTHESIS = "HYPOTHESIS"
UNRESOLVED = "UNRESOLVED"
CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True)
class RelView:
    id: str
    rel_type: str
    assertion_kind: str
    to_id: str
    transaction_ids: frozenset[str]


@dataclass(frozen=True)
class Classified:
    classification: str
    claim: str


CLAIMS = {
    "gateway_merchant": "A gateway record lists this account as the settlement account for this domain.",
    "mentioned_in": "A statement narration contains this exact host or address.",
    "same_payment": "Two statement rows cite the same structured reference.",
    "infrastructure_overlap": (
        "The observations contain the same address or provider string. "
        "Whether the two share an operator is unresolved."
    ),
}


def classify(rows: list[RelView]) -> dict[str, Classified]:
    result: dict[str, Classified] = {}
    gateways = [row for row in rows if row.rel_type == "gateway_merchant"]
    mentions = [row for row in rows if row.rel_type == "mentioned_in"]
    for row in rows:
        claim = CLAIMS.get(row.rel_type, "")
        if row.rel_type == "infrastructure_overlap":
            result[row.id] = Classified(UNRESOLVED, claim)
            continue
        if row.assertion_kind == "hypothesis":
            result[row.id] = Classified(HYPOTHESIS, claim)
            continue
        if row.assertion_kind == "inferred":
            result[row.id] = Classified(INFERRED, claim)
            continue
        if row.rel_type == "gateway_merchant":
            rival = any(
                other.id != row.id
                and other.to_id != row.to_id
                and other.transaction_ids & row.transaction_ids
                for other in gateways
            )
            if rival:
                result[row.id] = Classified(CONTRADICTED, claim)
                continue
            backed = any(
                other.to_id == row.to_id and other.transaction_ids & row.transaction_ids for other in mentions
            )
            result[row.id] = Classified(CORROBORATED if backed else DIRECTLY_SUPPORTED, claim)
            continue
        if row.rel_type == "mentioned_in":
            backed = any(
                other.to_id == row.to_id and other.transaction_ids & row.transaction_ids for other in gateways
            )
            result[row.id] = Classified(CORROBORATED if backed else DIRECTLY_SUPPORTED, claim)
            continue
        result[row.id] = Classified(DIRECTLY_SUPPORTED, claim)
    return result
