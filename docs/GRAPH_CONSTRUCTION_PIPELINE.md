# Graph construction pipeline

Construction is a pure function of the rows it is given. It does not insert,
and it does not record a separate construction run. The trace run id on an
edge is the analytical run that already exists. The same committed rows
produce the same edge ids: `tx:{transaction_id}` for a statement transfer and
`flow:{flow_id}` when a FIFO flow is kept as its own edge.

## Steps

1. Authorise the case. An unassigned caller receives 404.
2. Reject a hop count outside 1 to 5.
3. Load transactions whose statement is not superseded.
4. Apply the booking-date window, if one was requested.
5. Load the requested succeeded trace, or the latest succeeded trace. A
   running or failed trace contributes no flows.
6. Pair the two statement sides of one payment when the reference, amount,
   currency, and accounts match. That is one edge. Both transaction ids stay
   on it. A repeated transaction id does not create a second edge.
7. Attach `layer_to` and `trace_run_id` to that edge when a FIFO flow has the
   same ends, amount, currency, and assertion. If the amount or the assertion
   differs, the FIFO flow is a second edge. A cash debit points at a
   `cash_exit` node. No destination account is created.
8. Copy residuals onto the holding account. `outside_horizon` is not drawn as
   a transfer to the next account.
9. If `focus` is set, drop nodes farther than `max_hops` and set `truncated`.
10. Label components and, when asked, one shortest path. Discard the graph.

A later statement that sets `supersedes_statement_id` removes the older
statement from the next response. The previous trace rows remain stored.

Account identity is the existing instrument key: the same normalised number
and IFSC, or the same VPA, are already one `accounts` row. The builder does
not merge on similar numbers or similar names.
