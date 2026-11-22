# Fund-flow tracing

Two different results can be requested. They are not interchangeable.

## `fifo.v1`

Policy `fifo`, version `fifo.v1`. Horizon default 3, allowed range 1 to 5.
Currency is a parameter. Amounts in another currency are not converted and are
not allocated.

Order is `booking_date`, then `booking_time` with nulls last, then
`line_number`, then transaction id. ADR 0010. If any in-scope row is
date-only, the limitations say file order is not clock order.

A credit reduces an earlier debit on the same account only when the reference
is non-empty and equal, the currency matches, and the credit is less than or
equal to the unmatched remainder. Otherwise it is not netted.

A seed debit emits layer 1 from that debit's remaining amount and queues a lot
on the named destination at layer 1. A seed credit queues a lot on that
account at layer 0. The next debit spends the oldest lots. One flow is emitted
per lot consumed. `layer_to` is the lot's arrival layer plus one.

When the next layer would exceed `max_layer`, the amount stays on the account
that holds it as `outside_horizon`. That account is not described as the
beneficiary. A cash debit has no destination. A named destination with no
statement in the case still receives the flow, plus `no_onward_record` for the
same amount. That residual is not extra money.

A mirror credit is the other side of a debit: same reference, same amount,
same currency, and the accounts point at each other. It is not a second
inflow. The same amount on the same day with a different reference is not a
mirror.

Unrelated credits do not receive the seed's complaint. A debit larger than the
attributed lots emits only the attributed part.

Conservation is per account, currency, and complaint: attributed outflow is at
most attributed inflow plus `0.01`, counting the seed introduction as inflow
at the account where the seed value enters. The sum of hop amounts is not
compared with the seed. If the check fails, status is `failed` and no flows
or residuals are stored.

Both structured sides with the same reference use assertion `verified` and
method `reference_join`. A structured counterparty without the other statement
uses `structured_counterparty`. A narration-resolved counterparty is
`inferred`. The flow is an allocation under this policy. It is not proof that
the same funds moved through every account.

`POST /api/v1/cases/{case_id}/traces` runs this. `GET /api/v1/traces/{id}`
reads it. Account numbers in the response are masked. The stored flow uses
account ids.

## `statement_walk.v1`

`POST /api/v1/cases/{case_id}/statement-walks` walks verified structured-field
edges forward or backward from one account. Narration edges are excluded.
Amount and date filters drop edges before the walk. Depth stops at
`max_layer`. A repeat of an account already on the path stops that path with
`returned_to_earlier_account`. That stop is not a `CYCLE` indicator.

The finding is `hypothesis`. The limitations say the sequence is observed and
is not a FIFO allocation. Paths are stored on `analytical_runs.output`. They
are not `trace_flows`.

## Worked synthetic chain

Seed the victim debit `S1-V` of `100000.0000` INR, horizon 3. Flows are
V→I1, I1→I2, I2→I3. Residual `100000.0000` on I3, reason `outside_horizon`.
Account B (`****0019`) is not a flow destination. Horizon 4 adds I3→B and
publishes no residual. The three hop amounts sum to `300000.0000` and are not
checked against the seed.
