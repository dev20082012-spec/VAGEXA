# Architecture decision records

Accepted decisions for VAGEXA. A later change that reverses one of these adds a
new record. It does not rewrite history in the old file.

| Record | Decision |
| --- | --- |
| [0001](0001-postgresql-system-of-record.md) | PostgreSQL is the system of record |
| [0002](0002-python-fastapi-backend.md) | Python and FastAPI form the application backend |
| [0003](0003-react-typescript-spa.md) | React and TypeScript form a single-page client |
| [0004](0004-derived-graph-networkx.md) | NetworkX on a derived, case-scoped graph; Neo4j is conditional |
| [0005](0005-postgres-job-queue.md) | A PostgreSQL job table is the first queue |
| [0006](0006-evidence-and-assertion-kinds.md) | Three assertion kinds and append-only evidence |
| [0007](0007-fifo-tracing-policy.md) | FIFO is the default, versioned tracing policy |
| [0008](0008-copilot-over-tools.md) | The copilot narrates tool results |
| [0009](0009-proprietary-licence-placeholder.md) | Proprietary licence with an unconfirmed owner |
| [0010](0010-trace-conservation-and-fifo-order.md) | Per-account conservation and a total FIFO order |
| [0011](0011-infrastructure-overlap-is-not-ownership.md) | Shared infrastructure is overlap, not ownership |
| [0012](0012-statement-subject-and-reprocessing.md) | Statement subject is required; reprocessing appends |
| [0013](0013-instrument-and-observation.md) | Instrument keys are immutable; printed details are observations |
| [0014](0014-audit-product-choices.md) | Owner decisions on indicators, horizon, admin access, and copilot |
| [0015](0015-analysis-methods-for-prompt-07.md) | FIFO, indicators, and an observed walk; deferred cycle and risk scores |
| [0016](0016-derived-graph-without-ranking.md) | Derived NetworkX case graph; no centrality or community rank |
| [0017](0017-gateway-bridge-and-display-classification.md) | Gateway bridge records and a read-time relationship classification |

Status values: `accepted`, `superseded`. None are superseded. ADR 0010 adds the
conservation formula and sort order that ADR 0007 left open. ADR 0007 remains
the decision that FIFO is the default policy.
