# Hackathon backend test results

Date: 2026-11-22. Every line below was executed in this workspace.

## Automated

| Command | Result |
| --- | --- |
| `python -m ruff check src tests` | Passed |
| `python -m ruff format` | 75 files formatted |
| `python -m mypy src` | Passed, 60 source files |
| `python -m pytest -q` | **84 passed**, 1 Starlette deprecation warning |
| `npx eslint src`, `npx tsc --noEmit` | Passed |
| `npx vitest run` | 2 passed |
| `npx vite build` | Passed. Main chunk 761 kB, over Vite's 500 kB warning |

`tests/test_demo_workflow.py` checks the 14 acceptance points against
`demo.ground_truth()`:

| Point | Check |
| --- | --- |
| Seed exists, repeat is safe | Two seed runs. Counts of the case, transactions, DNS rows, gateway rows, relationships, and analytical runs are identical |
| Case and summary | Reference, synthetic notice, 23 transactions, 12 statements |
| Transactions | 23 rows through the API |
| Trace | Three hops, residual on `****0013`, nothing to `****0019`, `reference` on the first hop |
| Findings | `FAN_IN` and `FAN_OUT` on `****0030` |
| Observations | `syn-a.test` history has both addresses |
| Bridge evidence | Gateway record readable, merchant `syn-a.test`, payee `****0011` |
| Classification | `gateway_merchant` and `mentioned_in` are `CORROBORATED`. Overlap is `UNRESOLVED` with the exact limitation |
| Unsupported links | No account link to `syn-b.test`, `syn-c.test`, or `syn-aa.test`. No bridge edge to `syn-b.test` on the graph |
| Graph integrity | Account and domain nodes exist in the database. Every edge has support. Each bridge support item opens with 200 |
| Unauthorized | Unassigned investigator: summary, graph, relationship evidence, and a single evidence record all 404 |
| Restart | Two new application instances read the same case and counts |
| Contradiction | Two gateway rows on one statement row for different domains are both `CONTRADICTED` |

`tests/test_db_scope.py` checks that the database dependency commits before
the response and that no router uses the old request-scoped dependency.

## Live, on `127.0.0.1:8000`

| Check | Result |
| --- | --- |
| `alembic upgrade head` on the app database | `20261122_0007 (head)` |
| `python -m vagexa.demo_seed --username investigator`, twice | Same case id both times |
| Sign-in followed at once by `/me` and `/cases`, 20 times | 0 failures after the fix below |
| Summary | 12 statements, 23 transactions, 4 DNS, 2 hosting, 1 gateway, 12 relationships: 2 `CORROBORATED`, 8 `DIRECTLY_SUPPORTED`, 2 `UNRESOLVED` |
| Graph | 28 nodes, 25 edges, kinds `gateway_merchant`, `hosted_with`, `infrastructure_overlap`, `mentioned_in`, `resolves_to`, `transfer`. No edge without support |
| Bridge evidence | Gateway record and both statement rows returned 200, `synthetic` |
| After API restarts | The case and its counts were unchanged |

## Defect found and fixed

FastAPI 0.165 ends a `yield` dependency after the response by default. The
session's commit therefore ran after the login response was sent. A client
that called `/me` immediately could arrive before the session row existed and
receive 401. This happened intermittently on the live API. The database
dependency now uses `scope="function"`, so the commit finishes first. The
20-attempt check above was run after the change.

## Not tested

No public deployment, no browser click-through of the signed-in pages, no
load test, and no `EXPLAIN` plan.
