# Graph intelligence engine

The graph is a response. PostgreSQL holds the accounts, transactions, trace
flows, and residuals. `intelligence/graph/build.py` turns those rows into a
NetworkX `MultiDiGraph` and the API discards it. ADR 0004 and ADR 0016.
There is no Neo4j database and no `graph_nodes` table to keep in step with
the ledger.

## What a request returns

`GET /api/v1/cases/{case_id}/graph` is limited to the caller's case. `max_hops`
defaults to 3 and is rejected above 5. `focus` keeps accounts within that many
undirected hops and sets `truncated` when something is omitted. Transfer
direction stays on the edges.

Optional `booking_date_from` and `booking_date_to` drop transfers outside the
window. Optional `path_from` and `path_to` ask for one directed shortest path.
The path is omitted when it would be longer than `max_hops`, when no directed
path exists, or when either account is outside the focused subgraph.

`GET /api/v1/cases/{case_id}/cross-case-signals` counts other cases that cite
the same normalised account key. The body is the masked key, the count, the
method `exact_identifier`, and a limitation. It does not contain the other
case's title or its transactions.

## What this release does not draw

Complaints, parties, findings, and investigations are not nodes. A transaction
is the evidence on a transfer edge. Infrastructure kinds (`domain`, `ip`) are
reserved in the data model and are not filled, because this release does not
load DNS or hosting observations and does not invent them.

Degree, betweenness, community detection, and a cycle code are not computed.
A component is a weakly connected set in the loaded subgraph. Connectivity is
not common ownership and not a criminal association.
