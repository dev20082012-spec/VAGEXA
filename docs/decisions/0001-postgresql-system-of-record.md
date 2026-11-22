# 0001. PostgreSQL is the system of record

- Status: accepted
- Date: 2026-11-22

## Context

VAGEXA must store money without rounding error, keep an append-only history,
and answer authorised case queries. Investigators also need graph traversal.
Those are different workloads, and putting both in a graph database from the
start would make evidence constraints and audit harder to enforce.

SQLite would make local tests easy and would omit the constraints the product
actually depends on: partial unique indexes, `inet`, trigger behaviour, and
the same engine as the demo.

## Decision

PostgreSQL 16 holds every authoritative record: identity, cases, transactions,
observations, relationships, jobs, evidence, and audit. Amounts are
`numeric(20, 4)`. Graph results are computed from these tables.

## Consequences

- One backup story and one transaction around ingest.
- Analytical code must tolerate SQL for the queries it runs often. That is
  acceptable at case scale with a hop cap.
- A second database is a later, explicit decision.

## Alternatives

- Neo4j as the system of record. Strong path queries. Weaker fit for decimal
  money, append-only evidence, and relational audit. Rejected for the
  authoritative store.
- PostgreSQL plus Apache AGE so Cypher sits in the same server. One process to
  operate, and an extension the rest of the design does not need yet. Rejected
  until a query is shown that SQL and NetworkX cannot do inside the hop cap.
- SQLite for the demo. Rejected because the demo would not exercise the real
  constraints.
