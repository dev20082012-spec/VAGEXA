# Graph provenance

The graph is not a second evidence store. Each transfer edge cites the rows
it was built from.

| Field | Meaning |
| --- | --- |
| `source_transaction_ids` | The statement rows. A paired debit and credit are both listed. |
| `evidence_ids` | Transaction evidence rows when analysis has already created them. Empty when none exist. The builder does not insert evidence. |
| `provenance_id` | The statement row's provenance. FIFO-only edges leave this empty and cite `trace_run_id` instead. |
| `method_name` and `method_version` | How the edge was formed: `reference_join`, `structured_counterparty`, `narration_extractor`, `cash_exit`, or the FIFO method on a separate allocation edge. |
| `assertion_kind` | `verified`, `inferred`, or `hypothesis`. There is no numeric confidence. |
| `trace_run_id` and `layer_to` | Present when the selected succeeded trace allocated that amount. |
| `explanation` | The limitation for that edge. |

Residuals sit on the account node: amount, currency, reason, and the trace
run. `outside_horizon` is not an edge to the next account.

There is no `valid_to`. History is the set of statements and trace runs.
Superseding a statement removes its transactions from the next graph. The
older analytical run is still in `trace_flows`. Audit rows for `graph.read`
and `cross_case.lookup` record the hop count and the signal count. They do
not record full account numbers.

An analyst correction of the underlying statement is a new statement row, not
an edit of the edge. The graph has no analyst-modified copy of its own.
