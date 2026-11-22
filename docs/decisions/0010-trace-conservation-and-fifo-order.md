# 0010. Per-account conservation and a total FIFO order

- Status: accepted
- Date: 2026-11-22

## Context

ADR 0007 selected FIFO and left the conservation check and the sort order
unspecified. The financial document then defined conservation as "the sum of
attributed flows cannot exceed the seed". That formula rejects every multi-hop
trace, because each hop emits another flow of the same value. The same
document said reversals "may" be netted, and it did not order rows that share
a booking date. `FR-EVD-05` requires two runs to produce the same amounts.

This record does not change the choice of FIFO. It removes an unimplementable
check and closes the order.

## Decision

`fifo.v1` orders candidate rows by `booking_date` ascending, then
`booking_time` ascending with nulls last, then `line_number` ascending, then
transaction id ascending.

A credit nets against an earlier debit only when `reference_raw` is non-empty
and exactly equal, the currency matches, and the credit amount is less than or
equal to the unmatched remainder of that debit. Otherwise the credit is not
netted.

Conservation is per account, per currency, and per complaint: attributed
outflow is less than or equal to attributed inflow at that account, plus a
seed credited there, within `0.01`. The sum of flow amounts across layers is
not compared with the seed.

When either side of a pass-through test has `time_precision = date`, the dwell
condition is not applied and the limitation says so. Missing times are not
stored as midnight.

## Consequences

- Multi-hop fixtures become valid tests.
- Same-day statement rows follow file order when the bank did not supply a time. The run must say that.
- ADR 0007 remains the decision that FIFO is the default policy.

## Alternatives

- Keep the global sum. It cannot accept a chain. Rejected.
- Leave reversals optional. Two implementations would both claim `fifo.v1`. Rejected.
- Impute midnight for date-only rows. That invents evidence. Rejected.
