# Hackathon MVP status

Audit date: 2026-11-22. Deadline: 24 November 2026, 23:00 IST.

This is what runs. It is not a completion percentage. Tests passing does not
mean a judge can open one investigation and see the story.

## Commands executed

| Check | Result |
| --- | --- |
| `python -m ruff check src tests` | Passed |
| `python -m mypy src` | Passed, 54 source files |
| `python -m pytest -q` | **79 passed**, 1 Starlette deprecation warning |
| `npx eslint src` | Passed |
| `npx tsc --noEmit` | Passed |
| `npx vitest run` | 2 passed. These tests cover the shell and an empty state, not the investigation pages |
| `npx vite build` | Passed. Main chunk 761 kB. Vite warned that it is over 500 kB |
| `GET /health/live` and `/health/ready` on `127.0.0.1:8000` | 200 |
| Login and `GET /api/v1/cases` on that API | 200. Three local cases: `SYN-UI-07`, `SYN-LIVE-3`, `SYN-LIVE` |

Local API and Vite were already running. There is no public URL.

## What `SYN-UI-07` actually contains

20 transactions, a succeeded FIFO trace, 1 finding, 0 indicator rows, 2 DNS
observations, 0 hosting notes, 0 correlation proposals. The graph returned 18
nodes and 15 edges of kinds `transfer`, `resolves_to`, and
`infrastructure_overlap`. Certificate reason: `not_collected`.

The two domains were added after the statements. The statement narrations do
not contain those domain names, and correlation has not been run. The live
case therefore does not yet show a financial-to-domain bridge.

## Status matrix

| Feature | Frontend | Backend | Database | Integration | Actual status | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Login and access control | Sign-in, session, CSRF | Cookie session, roles, case assignment | Users, sessions, assignments | Login works on the live API | WORKING | P0 |
| Investigation dashboard | Case list only | Case list | Cases | No key entities, findings, or activity on the first screen | NOT IMPLEMENTED | P0 |
| Investigation creation | Open-case form | Create case, creator becomes lead | Cases, assignments | Works | WORKING | P1 |
| Investigation detail workspace | Title, status, five links | Get case | Cases | Does not show transactions, findings, or evidence | PARTIALLY WORKING | P0 |
| Financial dataset upload | File form on the statements page | CSV and JSON ingest, idempotent re-upload | Statements, transactions, issues | Works when a user uploads. Nothing is preloaded | WORKING | P0 |
| Transaction explorer | Table, currency, date, amount filters | Paginated list and detail | Transactions | List is wired. The UI does not open transaction detail or the original record | PARTIALLY WORKING | P1 |
| Account activity | Summary table on the analysis page | `financial-summary` and `activity` | Transactions | Wired. Empty until statements exist | WORKING | P1 |
| Multi-hop fund tracing | FIFO form, flows, residuals | `fifo.v1`, horizon 1–5 | Trace tables | Works in tests. `SYN-UI-07` has a succeeded trace | WORKING | P0 |
| Fan-in and fan-out | Indicator form | `indicators.v1` | Indicator rows | Works in tests. `SYN-UI-07` has zero indicator rows | BACKEND ONLY on the live case | P0 |
| Suspicious pattern findings | Findings table | Findings with limitations | Findings, support | One finding exists on `SYN-UI-07`. No pass-through, cycle, or score | PARTIALLY WORKING | P0 |
| Graph construction | None by itself | NetworkX response, not stored | Reads transactions, flows, observations | Live graph returned 18 nodes | WORKING | P0 |
| Interactive graph | Cytoscape canvas, legend, selection | Same graph endpoint | None | Code calls the API. A signed-in click-through was not repeated in this audit | PARTIALLY WORKING | P0 |
| Domain investigation | Manual form and table | Normalised domain rows | `domain_names` | Only domains someone typed | PARTIALLY WORKING | P0 |
| DNS and IP observations | Form, import, disabled lookup | A and AAAA only. Lookup returns 409 | `dns_observations`, `ip_addresses` | Two DNS rows on `SYN-UI-07`. No history view beyond the table | PARTIALLY WORKING | P0 |
| Infrastructure relationships | Shown if present on the graph | Overlap derived at read time | Observations | One overlap edge on the live graph. Limitation is non-ownership | WORKING when observations exist | P0 |
| Unified correlation | Run, list, confirm, reject | `correlate.v1` | Relationships, reviews | Works in tests. Zero proposals on `SYN-UI-07` | BACKEND ONLY on the live case | P0 |
| Supporting evidence inspection | Provenance prefix, support id prefix | Transaction detail includes `original_record` | Provenance, evidence | No evidence screen. Narration is not shown in the transaction table | BACKEND ONLY | P1 |
| Investigation report | None | None | Evidence kind `report` exists unused | No HTML or PDF export | NOT IMPLEMENTED | P1 |

## Not built

Copilot, HTML report, complaints, certificates, RDAP, ASN, live DNS, centrality,
community detection, and a public deployment. README still says the next task
is statement ingest. That sentence is stale.
