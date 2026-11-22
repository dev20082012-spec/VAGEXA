# Hackathon demonstration QA

Date: 2026-11-22. One case, `SYN-DEMO`. This is the record of what was
checked for the demonstration scenario. It is not a certification.

## 1. Primary investigation

Reference `SYN-DEMO`. Case id on this machine
`5aba51a4-0ce0-4bff-967b-534866b5d4f0`. Status `open`. Opened `2026-01-20`.
Classification `synthetic`. Generator `demo.v2`. Seed `20261122`.

Title, which the workspace uses as the objective: "Determine which records
connect a fictional merchant payment to later transfers, and which links
remain unresolved."

## 2. Scenario

A fictional merchant payment of `100000.0000` INR moves across three
allocated hops. A separate account shows fan-in and fan-out. One gateway
record and one narration name `syn-a.test`. A second domain shares that
host's address and stays unresolved. A later `2500.0000` payment has two
disagreeing gateway records, both retained. Ordinary and unrelated payments
are present so the detectors have something they should not join up.
Narrative and timeline: [Demo scenario](HACKATHON_DEMO_SCENARIO.md).

## 3. Records

14 statements, 25 transactions, 6 DNS observations, 2 hosting notes, 3
gateway records, 15 relationships, 18 findings. Debits `604819.5000`. Credits
`607500.0000`. The difference is missing counterpart statements, not a
balancing entry. Dictionary: [Demo data dictionary](HACKATHON_DEMO_DATA_DICTIONARY.md).

## 4. Financial validation

Transaction search, own-account totals, and the debit and credit sums matched
the ground truth. No float was used. Details:
[Analytical validation](HACKATHON_ANALYTICAL_VALIDATION.md).

## 5. Fund-flow tracing

`fifo.v1`, horizon 3, seed `DEMO-V-1`. Hops `****0001` → `****0011` →
`****0012` → `****0013`. Residual `100000.0000` `outside_horizon` on
`****0013`. `****0019` is on a statement edge and is not in the allocation.
The disputed payment and the unrelated transfer are not in the allocation.

## 6. Pattern detection

`FAN_IN` and `FAN_OUT` on `****0030` only, window 16–17 January 2026,
`indicators.v1`. `PASS_THROUGH` did not match at ratio `0.85`. `****0060`
did not match. No false positive and no missing expected hit in this case.

## 7. Infrastructure

Six DNS rows, including both `syn-a.test` answers, and two hosting notes.
Resolver `synthetic_fixture`. No certificate, nameserver, ASN, or
geolocation row. The later DNS answer is history, not a contradicted
relationship.

## 8. Bridge evidence

`SYN-PG-0001` names reference `UTRSYN0001`, payee `****0011`, and
`syn-a.test`. The statement rows with that reference are the financial side.
The narration on `DEMO-V-1` names the same host. The record is marked
synthetic in the API.

## 9. Correlation

| Scenario | Result |
| --- | --- |
| A. Explicit bridge | `CORROBORATED`, `proposed` |
| B. Shared address and shared provider | `UNRESOLVED`, non-ownership limitation |
| C. Time overlap only | No relationship created |
| D. Missing identifier | No account link to `syn-aa.test`, `syn-b.test`, or `syn-c.test` |
| E. Two gateway records | Both kept, both `CONTRADICTED`, `proposed` |

Live cross-domain counts: `CORROBORATED` 2, `CONTRADICTED` 2. Overlaps: 2.
Method `correlate.v2`. No confidence score was introduced.

## 10. Graph

Live graph: 34 nodes and 30 edges. The test checked that every edge has
support and that its ends are nodes in the payload. The opening transfer and
the disputed transfer have the statement direction and amount. The
corroborated gateway edge is distinct from the two contradicted edges.
`same_payment` is not drawn again.

The interface selects the corroborated gateway link when a screen asks for
the bridge, including when a contradicted gateway row is earlier in the list.
That selection is covered by a frontend test.

## 11. Evidence and provenance

Synthetic classification is on the case and on the opened source records.
Repeated seeding does not duplicate source rows or relationships. Findings
carry limitations and method versions. An unassigned investigator receives
404. Full notes: [Evidence validation](HACKATHON_EVIDENCE_VALIDATION.md).

The ground-truth document is not part of the investigator interface.

## 12. Frontend consistency

The dashboard, overview, report, and summary use the API counts. The live
summary returned 25, 14, 6, 2, 3, 18, and 15 for transactions, statements,
DNS, hosting, gateway records, findings, and relationships. Activity totals
for the checked accounts match the transaction rows. The report lists only
relationships returned by the API.

The sign-in page was opened at `http://127.0.0.1:5173/login`. It states that
the deployment holds synthetic demonstration data. A signed-in click through
the eight screens was not repeated in the browser in this session. The same
investigator account was checked through the live API, which returned the
summary, the three gateway classifications, and the graph counts above.

## 13. Script and rehearsal

The judge path is [Demo script](HACKATHON_DEMO_SCRIPT.md). The in-app guide
follows the same case in nine steps, starting at **Start the guided
walkthrough**. The API checks cover every record that script asks the judge
to see. The canvas itself was not clicked in this session. If it fails, the
script stays on Unified intelligence.

## 14. Automated tests

| Command | Result |
| --- | --- |
| `python -m pytest -q` | 84 passed, 51.07s, one Starlette deprecation warning |
| `python -m mypy src` | Passed, 60 files |
| `python -m ruff check` on the changed backend files | Passed |
| `npx vitest run` | 6 passed |
| `npx tsc --noEmit` | Passed |
| `npx eslint` on the changed frontend files | Passed |

`tests/test_demo_workflow.py` loads the seed twice, then checks the
transaction totals, the trace, the indicators, the five correlation
scenarios, the graph direction and amount, the evidence labels, idempotent
counts, and an unassigned caller's 404.

## 15. Remaining P0 defects

None were found in this pass. The signed-in browser rehearsal of the graph
canvas is the item not repeated here. It is not a data defect: the graph
payload was read from the live API.

## 16. Recommended next task

Rehearse [Demo script](HACKATHON_DEMO_SCRIPT.md) once while signed in, on the
machine that will be used for the submission, and confirm the network canvas
draws the corroborated edge. Do not add another scenario before that
rehearsal.
