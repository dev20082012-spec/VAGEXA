# 0017. Payment-gateway bridge records and a display classification

- Status: accepted
- Date: 2026-11-22

## Context

The hackathon demo needs one defensible link between a payment and a domain.
`correlate.v1` could only use text that a narration happened to contain. The
prompt also asked for six relationship words, while ADR 0006 allows three
stored assertion kinds.

## Decision

A `gateway_records` table holds a payment-gateway record as a source row. It
names a payment reference, the payer and payee accounts, a merchant domain,
an amount, and a processing time. `correlate.v2` adds one rule,
`gateway_merchant`: a gateway record links its payee account to its merchant
domain only when a structured statement row has the same reference, amount,
and currency, and runs from that payer to that payee. Without that statement
row, nothing is proposed. The assertion is `verified` for what the record
states. The limitation says the record does not identify who operates the
domain.

The six words are a display classification computed when the API reads the
rows. They are not stored, and they do not change `assertion_kind`:

| Label | When |
| --- | --- |
| `DIRECTLY_SUPPORTED` | A single verified source field states the claim |
| `CORROBORATED` | A gateway record and a narration both tie the same statement row to the same domain |
| `INFERRED` | Stored assertion `inferred` |
| `HYPOTHESIS` | Stored assertion `hypothesis` |
| `UNRESOLVED` | Infrastructure overlap. The shared key is observed. Whether the two share an operator is unresolved |
| `CONTRADICTED` | Two gateway records tie the same statement row to different domains |

## Consequences

- Rows written by `correlate.v1` keep their stored version.
- A shared address or provider string never becomes `CORROBORATED`, and
  never creates an account-to-domain link.
- Review status is still `proposed`, `confirmed`, or `rejected`.

## Alternatives

- Store the six words as a fourth assertion column. That reverses ADR 0006.
  Rejected.
- Link a domain to an account because they share a day. Time is not a key.
  Rejected.
