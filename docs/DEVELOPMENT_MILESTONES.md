# Development milestones

Work in this order. Do not start a milestone whose dependency is red.
Do not open FIFO, the graph, and the copilot in parallel with the first
migration.

Each milestone is one change set an engineer can review. Paths are the
package layout from the architecture document. They do not exist yet.

## M1 — Skeleton and access

| | |
| --- | --- |
| Objective | A synthetic case can be created and is invisible to an unassigned administrator. |
| Features | Package, Compose, migration from the database spec (including parties and annotations, with no routes for them yet), health, login, case create, assignment gate. |
| Modules | `api`, `application` auth and cases, `adapters/persistence`, `frontend` login and case list, `deploy` compose. |
| Dependencies | ADRs 0001–0006 and 0013–0014. |
| Acceptance | Health ready fails when Postgres is down. Unassigned administrator receives 404. Audit updates raise the append-only trigger. `official` case insert fails in synthetic mode. The transaction-table trigger is part of M2, when that table is created. See `docs/IMPLEMENTATION_STATUS.md`. |
| Tests | The database and API rows in the testing plan that do not need statements. |
| Evidence | CI log, or a local pytest log, plus `GET /health/ready` against Compose. |
| Risks | Encoding the pre-audit account columns. Review the migration against the database implementation spec before merge. |

## M2 — Statement ingest

| | |
| --- | --- |
| Objective | Scenario 1 CSVs become current transactions with file hash and line number. |
| Features | Upload, subject account, parser, worker, reprocess, holder observations. |
| Modules | `adapters/parsers`, `intelligence/financial` parse coordination, `worker`, transaction screen. |
| Dependencies | M1. |
| Acceptance | Missing subject rejects the job and writes no transactions. Duplicate hash does not double the rows. Two holder names for one instrument both remain. |
| Tests | Parser unit tests and the reprocess database test. |
| Evidence | A job reaches `succeeded` and the transaction list shows `100000.0000` as a string. |
| Risks | Guessing the subject account. The upload form must require it. |

## M3 — FIFO trace

| | |
| --- | --- |
| Objective | Horizon 3 attributes three hops and leaves a residual. |
| Features | `fifo.v1`, seeds, residuals, conservation, trace screen panel. |
| Modules | `intelligence/financial`, trace routes, workspace residual panel. |
| Dependencies | M2. |
| Acceptance | Scenario 1 matches the algorithm example. A second run has the same output hash. No flow to account B. |
| Tests | The FIFO unit list. |
| Evidence | Trace JSON in the test fixture output. |
| Risks | Summing hops and failing a correct chain. The test that would have failed C01 must stay. |

## M4 — Indicators and graph

| | |
| --- | --- |
| Objective | Verified fan-in and fan-out, and a graph that shows statement edges before a trace. |
| Features | `indicators.v1`, graph endpoint, Cytoscape screen, legend. |
| Modules | `intelligence/financial` indicators, `intelligence/graph`, graph feature. |
| Dependencies | M3 for FIFO edges. Statement edges can be tested from M2 data. |
| Acceptance | Fan-in fires at 3 and not at 2. Narration edges do not count. Hops above 5 are rejected. Legend contains the three assertion words. |
| Tests | Indicator and graph rows in the testing plan. |
| Evidence | Graph JSON from scenario 2 and a screenshot or browser note of the legend. |
| Risks | Painting high fan-out as guilt. Copy review is part of acceptance. |

## M5 — Infrastructure and cross-case

| | |
| --- | --- |
| Objective | Two domains, one IP, and a masked cross-case count. |
| Features | Manual observations, `correlate.v1`, signal endpoint. |
| Modules | `intelligence/digital`, `intelligence/correlation`, infrastructure screen. |
| Dependencies | M1. Can follow M2 in parallel with M3 only if the people are different. The default is after M4 so the demo is one path. |
| Acceptance | Overlap limitation is exact. No party row. One-case user does not receive the other title. |
| Tests | Correlation tests. |
| Evidence | Relationship row and signal JSON. |
| Risks | A live DNS call in the demo. The button must not exist. |

## M6 — Tools, notes, and report

| | |
| --- | --- |
| Objective | A named tool and an escaped report close the journey. |
| Features | Six tools, annotations, HTML export. |
| Modules | `intelligence/copilot`, `evidence`, report route, copilot and evidence screens. |
| Dependencies | M3 and M5 for a useful tool response. The escape test can be written earlier. |
| Acceptance | `trace_summary` cites fixture evidence ids. Report contains the residual reason and the non-guilt sentence. A script tag in a narration is escaped. 409 without a trace. |
| Tests | Copilot and HTML tests. |
| Evidence | Report file saved as a test artifact. |
| Risks | Keyword routing sneaking into the submit button. The UI spec forbids it. |

## M7 — Journey

| | |
| --- | --- |
| Objective | The ten demo steps pass on a clean stack. |
| Features | The scripted API journey and a browser pass. |
| Modules | Tests and a short operator note in the README once the commands are real. |
| Dependencies | M1–M6. |
| Acceptance | The end-to-end section of the testing plan. |
| Tests | That journey. |
| Evidence | CI job on Compose, plus a note of the browser pass. |
| Risks | Treating the API journey as a substitute for the screens. Both are required. |

## After M7

Do not start PDF, pro-rata, centrality, live DNS, or an LLM in the same
change as a defect fix. Those remain outside Phase 1.
