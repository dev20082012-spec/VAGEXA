# Hackathon analytical validation

Date: 2026-11-22. The expectations are
[Ground truth](HACKATHON_GROUND_TRUTH.md). Detectors ran on the stored rows.
Their output was compared with that document. It was not generated from it.

## How it was run

| Check | Result |
| --- | --- |
| `python -m ruff check` on the changed backend files | Passed |
| `python -m mypy src` | Passed, 60 source files |
| `python -m pytest -q` | **84 passed**, 1 Starlette deprecation warning, 51.07s |
| `npx eslint` on the changed frontend files, then `npx vitest run` | 6 passed |
| `npx tsc --noEmit` | Passed |
| `python -m vagexa.demo_seed --username investigator`, twice, on the local synthetic database | Same case id both times: `5aba51a4-0ce0-4bff-967b-534866b5d4f0` |
| Signed-in `GET /api/v1/cases/{id}/summary` on the running API at `127.0.0.1:8000` | 200. Counts and classifications below. |

The local case already had one correlation run. Adding the disputed payment
stored a second `correlate.v2` run and the three new proposals. The second
seed command did not store a third run. The trace run and the indicator run
were not repeated: the new rows are outside the indicator window and are not
the trace seed.

## Financial results

| Expected | Actual |
| --- | --- |
| 25 transactions, 14 statements | Matched, in the test API and in the live summary |
| Debits `604819.5000`, credits `607500.0000` | Matched by summing the transaction list with `Decimal` |
| `****0030` incoming `60000.0000` / outgoing `40000.0000` | Matched on `GET /activity` |
| `****0001`, `****0060`, `****0070`, `****0071` own-row totals in the ground truth | Matched |
| Three FIFO hops ending at `****0013` | Matched. Live trace `90d739e5-4a7e-4c24-b79c-53c31f9573d8`, `fifo.v1`, horizon 3, amounts `100000.0000` |
| Residual `outside_horizon` on `****0013` | Matched |
| `****0019`, `****0030`, `****0051`, `****0070`, `****0071` absent from the allocation | Matched |
| Opening graph edge `****0001` → `****0011`, `100000.0000` INR | Matched |
| Disputed graph edge `****0070` → `****0071`, `2500.0000` INR | Matched |
| `FAN_IN` support 3 and `FAN_OUT` support 4 on `****0030` | Matched. Assertion kind `inferred`. |
| No `PASS_THROUGH` | Matched |

No incorrect hop was allocated. The unrelated `100000.0000` transfer and the
`2500.0000` payment are on the statement graph and are not on the FIFO path.
`****0060` produced no indicator. No false positive was found in this case.
No expected indicator was missing.

Configuration recorded on the seed: window 2026-01-16 to 2026-01-17, fan-in
minimum 3, fan-out minimum 3, pass-through ratio `0.85`, dwell 24 hours,
amount floor `1000.0000`, currency `INR`.

## Infrastructure results

| Expected | Actual |
| --- | --- |
| Six DNS rows and two hosting notes | Matched |
| Both `syn-a.test` answers kept | Matched. Sorted answers `203.0.113.50` and `203.0.113.60`. |
| `syn-d.test` and `syn-e.test` on different addresses | Matched. They did not add an overlap. |
| Resolver `synthetic_fixture` | Stored on the DNS rows. No live lookup. |

Shared address and shared provider are relationship results, in the next
section. They are not ownership findings.

## Correlation results

Live signed-in summary: `cross_domain_by_classification` was
`{"CONTRADICTED": 2, "CORROBORATED": 2}` and `overlap_count` was 2.
All relationship classifications on the case were `CORROBORATED` 2,
`DIRECTLY_SUPPORTED` 9, `UNRESOLVED` 2, `CONTRADICTED` 2.

| Scenario | Expected | Actual |
| --- | --- | --- |
| A. Explicit bridge | `CORROBORATED` gateway link and `CORROBORATED` narration link for `syn-a.test` | Matched. `****0011` → `syn-a.test` and `****0001` → `syn-a.test`. Status `proposed`. Method `correlate.v2`. Assertion `verified` for the cited fields. |
| B. Shared IP and shared provider | Two `UNRESOLVED` overlaps, non-ownership limitation | Matched. The limitation text is the stored overlap sentence. |
| C. Time only | No link from `****0030` to `syn-b.test` | Matched. No relationship was created. |
| D. Missing identifier | No account link to `syn-aa.test`, `syn-b.test`, or `syn-c.test` | Matched. `DEMO-N-3` still contains `syn-aa.test`. `DEMO-D-OUT` contains no host. |
| E. Conflicting gateway records | Both records kept, both links `CONTRADICTED` | Matched. `****0071` → `syn-d.test` and `****0071` → `syn-e.test`, both `proposed`. |

`same_payment` count was 9. No numerical confidence was added.

## Graph results

On the live case the graph returned 34 nodes and 30 edges. That is 21
accounts, 5 domains, 7 addresses, and 1 provider; 16 transfer edges, 6 DNS
edges, 2 hosting edges, 2 overlap edges, 3 gateway edges, and 1 narration
edge. The test asserts that every edge ends on a node in the payload, that
every edge has support, and that account and domain nodes exist in the
database. The corroborated gateway edge is one. The contradicted gateway
edges are two. `syn-b.test` has no gateway or narration edge.

The opening transfer's direction, amount, and currency on the graph match the
transaction row. The FIFO path does not include the disputed payment.
