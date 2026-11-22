# Synthetic data strategy

`vagexa.synthetic.datasets` builds fictional datasets with seed `20261122`.
Account numbers begin with `900000000` and use IFSC `SYNB0000001`. They are
not real customer records.

| File | What it contains |
| --- | --- |
| `normal.csv` and `normal.json` | Two ordinary transfers, one date and one date-time |
| `mule_chain.csv` | Three debits along a chain. This is planted structure, not a discovered finding |
| `fan_in.csv` | Three sources into one account |
| `fan_out.csv` | One account to four destinations |
| `circular.csv` | A pays B and B pays A |
| `duplicate.csv` | The same source id and content twice |
| `invalid.csv` | Five decimal places |
| `missing.csv` | No destination |
| `currencies.csv` | USD plus a `DD/MM/YYYY` date |

`ground_truth()` lists the source ids that should be inserted and the issue
categories. Tests call it. The API does not. A synthetic case banner remains
the way an investigator sees that the rows are not official activity.

`intelligence_statements()` is a separate statement-shaped fixture for the
chain in the data validation report, plus fan-in, fan-out, and an unrelated
pair of the same amount. `analysis_ground_truth()` records the expected hops
and the accounts that must not appear. Tests compare the engine with that
dictionary. The API does not serve it, and a passed test is not a finding.
