# 0016. The case graph is derived, and it does not rank accounts

- Status: accepted
- Date: 2026-11-22

## Context

Prompt 08 asked for a graph database, stored construction runs, degree and
betweenness centrality, community detection, and a cycle finder. ADR 0004
already chose a NetworkX view that is discarded after the response. The graph
specification says degree, betweenness, and community detection are not
computed. ADR 0015 already keeps cycle labels out.

## Decision

The investigation graph is built in the request from current statement rows
and, when a succeeded trace exists, from that trace's flows and residuals.
Nothing is written to a graph store. Repeating the request against the same
rows returns the same node and edge ids.

Transactions stay evidence on edges. They are not nodes. Parties are not
drawn. Domain, IP, and hosting nodes are accepted by the model and are not
populated in this release, because no observation table is loaded and no
relationship is invented.

Weakly connected components are returned. They are not called communities.
A shortest path is returned only inside the hop cap of 5. Centrality,
community detection, and a cycle code are not computed.

A shared account key in another case is a count and a masked identifier.
The other case's title is not returned.

## Consequences

- There is no projection to synchronise.
- A superseded statement disappears from the next response. The old trace run
  remains in its own tables.
- The canvas draws this payload. Layout coordinates are not saved.

## Alternatives

- Persist `graph_nodes` now. A second copy of every edge, rejected until a
  measured query is too slow. ADR 0004.
- Rank accounts by betweenness. It answers a question the investigator did not
  ask and reads as importance. Rejected for this release.
