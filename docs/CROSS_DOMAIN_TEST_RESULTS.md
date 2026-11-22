# Cross-domain test results

Date: 2026-11-22. These are fixture results, not a rate of true crime links.

## Rules

| Case | Expected | Result |
| --- | --- | --- |
| Narration `https://syn-a.test/pay` and observed domain `syn-a.test` | One `mentioned_in`, `verified` | Matched. The salary narration on the same morning did not match. |
| `syn-aa.test` against known `syn-a.test` | No host match | No match |
| Domain observed, narration does not contain it | No proposal | Empty |
| Two domains, one address `203.0.113.50` | Overlap, exact limitation, `verified` | Matched. No party. |
| Two addresses, provider string `Synthetic Public Resolver` | Overlap, same limitation | Matched |
| Two structured rows, reference `UTR1`; a narration-pattern row with that reference | One `same_payment` for the structured pair | Matched |
| Re-run | `inserted` 0 | Matched on the API |
| Analyst confirm | 403 | Matched |
| Investigator confirm | Status `confirmed`, assertion still `verified`, reason stored | Matched |
| Second confirm | 409 | Matched |
| Unassigned read | 404 | Matched |
| Graph | `mentioned_in` edge present | Matched |

No numerical score is asserted, because none is produced.

## Commands

`python -m ruff check src tests` passed. `python -m mypy src` passed.
`python -m pytest -q` reported **79 passed**. The correlation cases are in
`tests/test_correlation.py`.
