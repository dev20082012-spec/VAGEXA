# 0013. Instruments are immutable keys; printed details are observations

- Status: accepted
- Date: 2026-11-22

## Context

Accounts, and similarly domains, were both a global identity and a mutable
profile. One holder name and one data classification sat on the account row.
Two statement files could not disagree. An update could erase the first name.
The same shape made a cross-case match and a synthetic-versus-official mix
hard to tell apart.

Cross-case matching needs a stable normalised key. Evidence needs every
printed value kept. Those are different rows.

## Decision

`accounts` stores the kind and the normalised key only: account number and
IFSC, or VPA. Those columns are not updated. There is no holder name on this
row.

`account_observations` stores the printed account number, holder name, and
bank name, with `case_id`, optional `statement_id`, `data_classification`, and
`provenance_id`. The table is append-only. Conflicting names are multiple
rows. The product does not choose between them.

Domains and IP addresses stay global keys. Facts about them are observations.
A case's interest in a key is a case-scoped relationship or observation, not a
null `case_id` on a global secret.

Synthetic and official populations stay in separate databases. The unique key
is unique inside one database. A relationship whose two ends are in different
data modes is still rejected.

## Consequences

- Scenario 6 is representable.
- Authorisation for reading an instrument is "assigned to a case that has an
  observation, transaction, or relationship citing it", not "knows the UUID".
- ADR 0001 is unchanged: Postgres remains the system of record.

## Alternatives

- Case-scoped duplicate account rows, matched by a query on the normalised
  columns. Also workable, and it copies every attribute into each case.
  Rejected for the key itself, because the cross-case signal then depends on
  a string match that can drift if normalisation changes in only one copy.
  Observations are still per case either way.
- Keep a single holder column and write "the latest". That deletes a conflict.
  Rejected.
