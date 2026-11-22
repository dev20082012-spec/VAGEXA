# Hackathon ground truth

This file is the reading copy of `vagexa.synthetic.demo.ground_truth()`.
Tests import that function and compare it with the API. The function is not
an HTTP response. The investigator workspace does not show this document, and
the case summary does not contain the word "ground" or the word "victim".

The expectations below were written from the scenario, then checked. They are
not copied out of a detector and then treated as the detector's discovery.

Checked on 2026-11-22 against a fresh test database and against the local
`SYN-DEMO` case after `python -m vagexa.demo_seed --username investigator`.

## Case

| Field | Expected |
| --- | --- |
| Reference | `SYN-DEMO` |
| Title | Determine which records connect a fictional merchant payment to later transfers, and which links remain unresolved |
| Status | `open` |
| Opened | `2026-01-20` |
| Classification | `synthetic` |
| Generator | `demo.v2` |
| Seed | `20261122` |

## Financial expectations

| Check | Expected |
| --- | --- |
| Transactions, statements | 25, 14 |
| Sum of debit rows, sum of credit rows | `604819.5000`, `607500.0000` |
| `****0001` own rows | incoming `0.0000`, outgoing `100000.0000` |
| `****0030` own rows | incoming `60000.0000` in 3 rows, outgoing `40000.0000` in 4 rows |
| `****0060` own rows | incoming `45000.0000`, outgoing `2319.5000` |
| `****0070` / `****0071` own rows | outgoing `2500.0000` / incoming `2500.0000` |
| Trace seed | `DEMO-V-1` |
| Method, horizon, currency | `fifo.v1`, 3, `INR` |
| Allocated hops | `****0001` → `****0011` → `****0012` → `****0013` |
| Residual | `100000.0000` `outside_horizon` on `****0013` |
| Not in that allocation | `****0019`, `****0030`, `****0051`, `****0070`, `****0071` |
| Opening graph edge | `****0001` → `****0011`, `100000.0000` INR, reference `UTRSYN0001`, booked 2026-01-15 09:00:00 |
| Disputed graph edge | `****0070` → `****0071`, `2500.0000` INR |
| Indicator window | 2026-01-16 to 2026-01-17 |
| Indicator settings | fan-in minimum 3, fan-out minimum 3, pass-through ratio `0.85`, currency `INR` |
| Indicator hits | `FAN_IN` and `FAN_OUT` on `****0030` only |
| `PASS_THROUGH` | Does not match |

`****0019` remains on the statement graph. The trace does not call that
account the beneficiary. The statement edge and the allocation are different
claims, and both are shown as such.

## Infrastructure expectations

| Check | Expected |
| --- | --- |
| DNS rows, hosting notes | 6, 2 |
| `syn-a.test` answers, both kept | `203.0.113.50`, then `203.0.113.60` |
| Shared address | `syn-a.test` and `syn-b.test` at `203.0.113.50` |
| Shared provider string | `203.0.113.70` and `203.0.113.71` |
| `syn-d.test` and `syn-e.test` | Different addresses. No overlap from those two hosts. |

The later `syn-a.test` answer is history. It is not a `CONTRADICTED`
relationship. The engine has no rule that turns a later DNS answer into that
classification.

## Correlation expectations

| Scenario | Input | Expected |
| --- | --- | --- |
| A. Explicit bridge | `SYN-PG-0001` plus the `UTRSYN0001` statement rows, and the narration on `DEMO-V-1` | One `gateway_merchant`, `****0011` → `syn-a.test`, `CORROBORATED`, `proposed`, `verified`. One `mentioned_in`, `****0001` → `syn-a.test`, same classification. |
| B. Shared address | The two DNS rows for `203.0.113.50`, and the two hosting notes | Two `infrastructure_overlap` rows, both `UNRESOLVED`, with the non-ownership limitation. |
| C. Time only | `****0030` is active within minutes of the `syn-b.test` observation | No relationship between that account and that host. |
| D. Missing identifier | `DEMO-N-3` contains `syn-aa.test`. `UNREL` has no host and no gateway record. `DEMO-D-OUT` names no host. | No `mentioned_in` for `syn-aa.test`, `syn-b.test`, or `syn-c.test`. |
| E. Conflicting records | `SYN-PG-0090` and `SYN-PG-0091` | Two `gateway_merchant` rows, `****0071` → `syn-d.test` and `****0071` → `syn-e.test`, both `CONTRADICTED`, both `proposed`. Both source records remain. |

Cross-domain counts: `CORROBORATED` 2, `CONTRADICTED` 2. Overlap count: 2.
`same_payment` pairs: 9, displayed as `DIRECTLY_SUPPORTED`, and omitted from
the graph because the transfer edge already cites both statement rows.

Relationship total: 15. Finding total: 18, which is one trace finding, two
indicator findings, and one finding per correlation proposal. Every finding
has a non-empty limitation and a method version.

## Non-findings

The case does not show who operates any domain, who holds any account, where
any address is, or whether any person committed an offence. It does not show
that `****0019` received the opening payment as a traced allocation. It does
not show that `syn-b.test` and `syn-a.test` have a common operator. It does
not show that `syn-d.test` or `syn-e.test` is the merchant for `UTRSYN0090`.
It does not show that the ordinary account `****0060` matches a fan-in,
fan-out, or pass-through rule.
