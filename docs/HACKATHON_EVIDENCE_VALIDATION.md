# Hackathon evidence validation

Date: 2026-11-22. This check covers `SYN-DEMO` only. It is not a claim of
forensic certification, legal admissibility, or a real investigation.

## What was checked

| Control | Result |
| --- | --- |
| Case classification | `synthetic` on the case, the summary notice, every gateway record returned by the API, and the evidence opened from the corroborated bridge. |
| Notice text | "Synthetic demonstration data. These accounts, domains, addresses, and gateway records are fictional and are not official records." |
| Original statement bytes | A repeated seed finds the same file hash and does not insert the transactions again. |
| Gateway identity | `SYN-PG-0001`, `SYN-PG-0090`, and `SYN-PG-0091` are stored once each. A repeated source id returns the existing row. |
| DNS history | Both `syn-a.test` answers remain. A later answer does not delete the earlier one. |
| Conflicting gateway records | Both `SYN-PG-0090` and `SYN-PG-0091` remain. The relationships are `CONTRADICTED` and `proposed`. Neither row was overwritten. |
| Bridge support | The corroborated relationship's evidence is one gateway record and two statement rows, including `DEMO-V-1`, whose narration contains `syn-a.test`. |
| Method version | Gateway relationships are `correlate.v2`. Gateway provenance method is `gateway_record.v1`. The trace is `fifo.v1`. The indicators are `indicators.v1`. |
| Findings | 18 findings. Each has a non-empty limitation and a method version. |
| Hidden labels | The summary JSON does not contain "ground" or "victim". |
| Authorisation | An investigator who is not assigned receives 404 for the summary, the graph, the relationship evidence, and a single evidence record. |
| Clocks | Statement evidence says the clock is printed as supplied and is not converted. Gateway evidence exposes `processed_at` in UTC. The two clocks are not treated as one timeline. |

## What each cross-domain link rests on

| Link | Financial record | Infrastructure record | Bridge | Matching identifier | Classification | Still unsupported |
| --- | --- | --- | --- | --- | --- | --- |
| `****0011` → `syn-a.test` | `UTRSYN0001` debit and credit | DNS for `syn-a.test` | `SYN-PG-0001` | Reference, amount `100000.0000` INR, payer, payee, merchant host | `CORROBORATED` | Who operates the host, and whether the account holder knew |
| `****0001` → `syn-a.test` | `DEMO-V-1` narration | The same DNS rows | The narration itself; the gateway record agrees on the host | Exact host `syn-a.test` | `CORROBORATED` | Use, ownership, or intent |
| `syn-a.test` → `syn-b.test` | None | Two DNS rows at `203.0.113.50` | None beyond the observations | The address | `UNRESOLVED` | A common operator |
| `****0071` → `syn-d.test` and `syn-e.test` | `UTRSYN0090` debit and credit | DNS for each host, on different addresses | `SYN-PG-0090` and `SYN-PG-0091` | The same reference, amount, and accounts, with two merchant hosts | `CONTRADICTED` | Which host, if either, the payment concerned |

## Corrections

Source rows, provenance, evidence, findings, and trace rows are insert-only
in the database. Relationship review is a new review row. This validation did
not submit a confirm or a reject, so the demo relationships are still
`proposed`. The seed updates only the case title and the synthetic-batch
version hash when those presentation fields differ. It does not delete rows,
and it is not run from application startup.

No official record was loaded. The deployment under test was `synthetic`.
