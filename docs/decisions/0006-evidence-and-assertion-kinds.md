# 0006. Three assertion kinds and append-only evidence

- Status: accepted
- Date: 2026-11-22

## Context

The product has to separate what a source record says, what an algorithm
derived, and what a person might investigate next. If those are collapsed into
one "link" with a confidence percentage, a later reader cannot tell a statement
row from a guess. A confidence percentage also reads like a chance of guilt.

Investigators in this project use the words verified, inferred, and hypothesis.
The data model keeps those words and defines them narrowly so "verified" cannot
drift into "proved".

## Decision

`assertion_kind` is one of `verified`, `inferred`, or `hypothesis`.

- `verified`: a cited source field states the claim.
- `inferred`: a named, versioned method produced the claim from verified inputs.
- `hypothesis`: a weak signal stored for review.

Provenance, evidence, transactions, observations, findings, trace outputs, and
audit events are append-only, enforced by database triggers in the first
migration. Corrections supersede. Relationship rows may update only their
decision columns, and that update is audited.

No column stores culpability.

## Consequences

- Reports and APIs must carry the kind even when it makes the payload longer.
- A confirmed hypothesis stays a hypothesis. Status and kind are different fields.
- Triggers make some mistakes loud. That is intended.

## Alternatives

- A single 0–1 score. Compact and easy to misuse. Rejected.
- The word `source_asserted` instead of `verified`. Clearer to engineers, and
  a second vocabulary for investigators. Rejected in favour of a strict
  definition of `verified` in [Evidence and provenance](../EVIDENCE_AND_PROVENANCE.md).
- Application-level discipline without triggers. Insufficient. One update
  statement would rewrite history.
