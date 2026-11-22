# 0004. NetworkX computes a derived, case-scoped graph

- Status: accepted
- Date: 2026-11-22

## Context

Investigators think in hops, fan-in, and shared beneficiaries. That is a graph.
The authoritative facts are relational and must stay transactional with
evidence. Loading a case-sized directed graph and running a bounded traversal
is a small-data problem if the hop cap is real.

Neo4j is a strong fit for large, persistent, multi-case traversals and for a
team that wants Cypher. It is also a second store to secure, back up, and keep
in agreement with PostgreSQL. Memgraph offers a similar Cypher-shaped option
with a smaller operational record for this project. Neither is justified by the
first scenario.

## Decision

Phase 1 and the default later design load a case subgraph from PostgreSQL and
run NetworkX in the API process. The in-memory graph is discarded after the
request. There are no `graph_nodes` tables until a measured need appears.

A graph database may be introduced only when all of the following are written
down in a new ADR:

- an interactive query that is too slow on a representative dataset after SQL
  and NetworkX have been measured;
- the projection direction is PostgreSQL to the graph store, and the graph
  store can be dropped and rebuilt;
- Cypher or the vendor query language stays inside an adapter;
- backups and access control for the new store are named.

Until that record exists, Neo4j is not a dependency.

## Consequences

- Cross-case work is an identifier query in SQL, not a global graph walk.
- Process memory bounds the graph. The hop cap and the case scope are what keep
  that honest.
- Algorithm code is unit-testable without a database container, apart from the
  loader.

## Alternatives

- Neo4j from day one. Better long-range graph tooling. Real consistency and
  operations cost. Deferred, not forbidden.
- Recursive SQL only, with no graph library. Enough for a fixed three-hop
  query, awkward for components and for tests that want a graph assertion.
  NetworkX is the smaller dependency that covers those tests.
- A persisted projection table immediately. Rejected until the request path is
  shown to be slow, so there is only one copy of an edge to get wrong.
