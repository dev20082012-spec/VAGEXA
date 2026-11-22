# Financial intelligence engine

The engine reads current statement legs and writes analytical runs. It does
not decide that an offence occurred.

## Modules

| Piece | Where it lives | What it does |
| --- | --- | --- |
| Ledger load | `application/analysis_service.py` | Current transactions for one case. Superseded statements are excluded. |
| FIFO allocation | `intelligence/financial/fifo.py` | `fifo.v1` |
| Indicator rules | `intelligence/financial/indicators.py` | `indicators.v1` |
| Observed sequence | `intelligence/financial/walk.py` | `statement_walk.v1` |
| Account activity | `intelligence/financial/activity.py` | Counts and decimal sums. Not a finding. |
| Findings | `findings` and `finding_support` | Method, version, limitations, evidence ids. |
| HTTP | `api/routers/analysis.py` | Auth, validation, response mapping. |

HTTP handlers do not allocate money or count fan-in. React renders the JSON
it receives.

## Run record

Every run stores `method_name`, `method_version`, the parameter object,
`input_hash`, and `output_hash` when the run succeeds. The input hash covers
the sorted ledger rows and the parameters. The same ledger and the same
parameters produce the same output hash. A second request inserts a new run.
It does not insert the transactions again.

A run is synchronous. The job row is created already `succeeded` or `failed`.
The response is that finished result. There is no progress figure before the
function returns.

The case bound is 10,000 current transactions and 20,000 published flows. Past
either bound the trace status is `failed` and no flows are stored. A statement
walk stops at 25 paths or 1,000 expansions.

## What this is not

`correlate.v1`, the case graph, the copilot, and a blended risk score are not
in this release. ADR 0015 records the detectors that were evaluated and not
shipped.
