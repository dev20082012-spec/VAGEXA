# Graph implementation specification

The graph is a response, not a store. PostgreSQL holds the facts. The API
loads a case-scoped subgraph, builds a NetworkX `MultiDiGraph`, and discards
it. ADR 0004. There is no second copy to synchronise.

## What is stored where

| Fact | Authoritative place | Graph |
| --- | --- | --- |
| Account key, transaction row, amount, date | Relational tables | A node id and an edge that cite those ids |
| FIFO attribution | `trace_flows` | An edge with `method_version=fifo.v1` and `trace_run_id` |
| DNS answer | `dns_observations` | A `resolves_to` edge with `observed_at` |
| Overlap limitation | `relationships.limitation` | The same text on the edge |
| Layout coordinates | Nowhere | Computed in the browser and not saved |

Repeating a request against the same committed rows returns the same node and
edge ids and properties. Positions may differ and are not evidence.

## Node types

| `kind` | Source id | Label |
| --- | --- | --- |
| `account` | `accounts.id` | Masked number or VPA |
| `complaint` | `complaints.id` | External reference or "Complaint" |
| `domain` | `domain_names.id` | `name_norm` |
| `ip` | `ip_addresses.id` | The address |
| `cash_exit` | `trace_flows.id` prefixed in the response as `exit:{flow_id}` | "Cash exit" |

Parties are not drawn in Phase 1. A cash exit is not an account.

## Edge types

Direction is `from` → `to` as stored. The response uses those ids.

| `kind` | Direction | When it is created | `assertion_kind` | Required properties |
| --- | --- | --- | --- | --- |
| `transfer` | Payer account to payee account, or to a cash exit | A current statement row with `counterparty_resolution=structured_field` or a `trace_flow` | `verified` for the structured field. `inferred` for FIFO and for `narration_pattern`. | `method_name`, `method_version`, `evidence_ids`, and for money `amount` as a string, `currency`. FIFO edges also have `trace_run_id` and `layer_to`. |
| `named_in` | Complaint to account or domain | `mentioned_in` whose text contains the key | `verified` for containment only | `limitation` that containment is not use or ownership |
| `resolves_to` | Domain to IP | One `dns_observations` row | `verified` against that observation | `observed_at`, `provenance_id` |
| `hosted_with` | IP to a provider string node is not used. The edge is IP to a synthetic label only when a hosting note names a provider. | `hosting_observations` | `hypothesis` for a typed note | `limitation` |
| `infrastructure_overlap` | Domain or IP to the other domain or IP that shares the key | The overlap relationship | `verified` for co-occurrence only | The non-ownership `limitation` from ADR 0011 |

Statement-backed `transfer` edges are included when no trace has been run.
A FIFO edge is added beside a statement edge when the amounts or assertion
kinds differ. They are not collapsed.

`shared_with_case` is not an edge in the graph payload for a caller who cannot
open the other case. That caller uses the cross-case signal endpoint.

## Provenance, time, and confidence

Every edge has `assertion_kind`, `method_name`, `method_version`, and at least
one of `evidence_ids` or `provenance_id`.

There is no numeric confidence and no probability of control. Support is the
list of evidence ids. A longer list is more support. It is not a score.

Temporal fields:

- Transfer edges carry `booking_date` from the source transaction.
- `resolves_to` carries `observed_at`. A later observation is a new edge.
  The old edge stays.
- Edges do not get `valid_to` in Phase 1. History is the set of observations.

## Traversal

Default `max_hops` is 3. The API rejects a value above 5.
Neighbourhood is undirected for membership and directed on the edges.
Path search, if called inside the service, uses `cutoff=max_hops`.
The client cannot submit a traversal expression.

Connected components are computed with `weakly_connected_components` on the
loaded subgraph and returned as `component`. The field is not named community,
gang, or network.

Degree, betweenness, and community detection are not computed. They would rank
accounts without a question the investigator asked. ADR 0014 and the Phase 1
scope leave them out.

## Load procedure

1. Authorise the case.
2. Reject `max_hops` above 5.
3. Select current statement transactions for the case (statement not superseded).
4. Select `trace_flows` for `trace_run_id` when the query includes one, otherwise the latest succeeded trace in the case, and also the statement edges even if that run is absent.
5. Select complaints, DNS observations, hosting notes, and relationships for the case.
6. Build the multigraph in memory.
7. If `focus` is set, keep nodes within `max_hops`.
8. Set `truncated` when the hop bound drops nodes.
9. Discard the graph.

Do not load another case's title or narrative.

## Five shapes

All identifiers below are the synthetic fixture. They are not real accounts.

### 1. Account A to B to C

V `100000000001` debits I1 `100000000011`, I1 debits I2 `100000000012`, I2
debits I3 `100000000013`. At horizon 3 the FIFO edges are layer 1, 2, and 3.
Account B `100000000019` is not an edge. It is a residual on I3. The graph
shows the residual as a node annotation on I3, `outside_horizon`, amount
`100000.0000`, and does not draw B as a transfer the policy attributed.

### 2. Many into one

A1, A2, and A3 each have a verified transfer into C `100000000030`. Three
`transfer` edges point at C. The indicator is a separate object, not a colour
that means mule.

### 3. One out to many

C has four verified transfer edges to D1–D4. Fan-out is the count of distinct
`to` accounts on verified edges. Narration-only edges are drawn dashed and
are not in that count.

### 4. Two investigations, one instrument

The graph for case SYN-A contains the account node for `100000000011`. It does
not contain SYN-B's complaint node. The signal endpoint returns the masked key
and `other_case_count`. A caller assigned to both cases may open SYN-B by its
own route. The service does not merge the two graphs in one response in
Phase 1.

### 5. Two domains, one IP, no ownership

`syn-a.test` and `syn-b.test` each have a `resolves_to` edge to `203.0.113.50`
with `observed_at`. An `infrastructure_overlap` edge between the domains
carries the limitation that a shared address does not establish common
ownership, common control, or a common operator. No party node is created.

## Consistency

The graph builder is a pure function of the rows it was given. It does not
insert. If a trace is still `running`, the builder does not include its flows.
A superseded statement's transactions are not loaded.
