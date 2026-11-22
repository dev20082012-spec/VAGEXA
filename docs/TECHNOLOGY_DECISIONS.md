# Technology decisions

This note re-evaluates the stack after the architecture audit. It does not add
a dependency. Volume figures are planning assumptions from
[Architecture audit](ARCHITECTURE_AUDIT.md) finding L04, not measurements.

The audit's conclusion on technology: the stack is larger than a hackathon
slide and smaller than a platform estate. The failures in the audit are
specification failures. They are not cured by Neo4j, a model service, or a
queue broker.

## PostgreSQL 16

1. Needed because money, authorisation, evidence, and jobs must commit together.
2. It solves exact decimal storage, constraints, append-only triggers, and case-scoped queries.
3. Essential for Phase 1, including the first migration.
4. SQLite omits the constraints the tests must hit. A graph database as the system of record makes audit and decimal money harder. Apache AGE adds Cypher inside Postgres before a query has been shown to need it.
5. One service in Compose. Operational cost is backups, roles, and upgrades, which Phase 4 already names.
6. Recommendation: keep. Do not add a second primary store.

## Python 3.12 and FastAPI

1. Needed for parsing, decimal allocation, NetworkX, and a typed HTTP boundary in one language.
2. It solves the rule that tracing must not be reimplemented in a second server.
3. Essential for Phase 1.
4. A Node.js API would share types with the browser and would split the financial rules into another process. Django adds an admin that is a poor fit for append-only evidence.
5. One image, two commands (API and worker). Low operational cost.
6. Recommendation: keep. Pandas stays out until a report genuinely needs a frame, and money rules stay in `Decimal` either way.

## React, TypeScript, and Vite

1. Needed for an authenticated workspace: tables, a graph drawing, upload, and a report download.
2. It solves investigator interaction without rendering case data on a public server.
3. Essential for the demo. Not essential for proving FIFO, which should be tested in Python first.
4. Next.js would server-render data this system should not put in an HTML cache. A server-only HTML UI cannot offer a usable directed graph.
5. A static build behind the web container. Node runs at image build time and is not a production service.
6. Recommendation: keep. Cytoscape.js is the drawing library when the graph screen is built. It is not a reason to compute paths in the browser.

## NetworkX

1. Needed for bounded paths and connected components on a case subgraph.
2. It solves in-process, testable graph operations without operating another database.
3. Essential when the graph and trace features are built. Not essential for the 1A skeleton.
4. Recursive SQL can express a fixed hop count and becomes awkward for "show the component and the assertion kind on every edge". Neo4j solves large persistent graphs and costs a second security boundary.
5. Library inside the API process. Memory is the limit. The hop cap and the case scope are what keep that limit real.
6. Recommendation: keep for case graphs. Do not add Neo4j on the strength of the word network. ADR 0004's trigger remains the only door.

## PostgreSQL job table

1. Needed because parse and trace must survive a process restart and show status.
2. It solves a durable queue without Redis.
3. Essential once uploads and traces exist. The health-check skeleton can land before the worker loop, but the table should be in the first migration if that migration is meant to be the last schema break.
4. Celery or RQ with Redis adds a broker the demo does not otherwise need. In-memory background tasks lose jobs.
5. The worker is another container of the same image. The operational duty is a lock timeout so a dead worker releases the row.
6. Recommendation: keep.

## Optional LLM adapter

1. Not needed to trace, count, match identifiers, or record DNS observations.
2. It would only phrase a tool bundle that the deterministic path already returns.
3. Not essential for Phase 1. Default remains `none`.
4. A chatbot with database access can invent entities. A vector store copies complaint text for a similarity feature nobody has specified.
5. A provider is a secret, an outbound dependency, and a prompt-injection surface.
6. Recommendation: do not enable it for the milestone. Keep the port so a later ADR can bind a provider without rewriting tools.

## Passive DNS and later RDAP, certificates, ASN

1. DNS is the only lookup that the public problem statement clearly implies, and only for names an investigator already has.
2. It solves a dated observation of a resolution. It does not solve attribution.
3. The live network call is not essential for the demo. Planted observations and a fake resolver are essential for the test.
4. A scanner would collect facts the investigator did not identify. That alternative is rejected.
5. Outbound queries reveal investigative interest to the resolver. The default stays off.
6. Recommendation: adapter and fake transport in the milestone. Live DNS is a switch, not a demo requirement. Certificate and RDAP tables wait for Phase 3.

## What was considered and left out

| Proposal | Why it stays out |
| --- | --- |
| Neo4j or Memgraph in Phase 1 | Cross-case work is an equality lookup. Case paths are short. A second store can drift from evidence. |
| Redis | The job table already provides durability. |
| A separate ML or feature service | No baseline, and a score would be read as suspicion. |
| Microservices per engine | The engines share one case and one transaction boundary. Splitting them makes provenance harder. |
| GraphQL | Easy to ask an unbounded graph question. The REST shape names the allowed queries. |
| Elasticsearch | Narration search is deferred, and a copy of narration is another disclosure store. |

No new runtime is recommended by this audit.
