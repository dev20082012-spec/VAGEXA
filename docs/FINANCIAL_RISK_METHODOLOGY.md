# Financial risk methodology

There is no universal fraud score and no risk-score table.

These stay separate:

| Question | What is stored |
| --- | --- |
| What pattern was detected? | Indicator code, or a trace or walk finding kind. |
| How was it produced? | `method_name` and `method_version` on the run and the finding. |
| What was assumed? | The parameter object: horizon, window, thresholds, currency. |
| What supports it? | `finding_support` rows pointing at transaction evidence. Evidence is not overwritten when a finding is added. |
| How sure is the link? | `assertion_kind`: `verified` on a structured flow, `inferred` on a rule match, `hypothesis` on an observed sequence. |
| What is missing or uncertain? | The non-empty `limitations` text, plus residual reasons `outside_horizon` and `no_onward_record`. |

Pattern severity, a confidence percentage, evidence quality, and investigative
priority are not folded into one number. No priority ranking is computed.
Thresholds are demonstration settings. A fired `FAN_IN` means the count of
verified sources met the stored minimum. It does not mean the account holder
committed an offence.

A failed conservation check publishes no flows. The run remains, with
`error_code=conservation`, so the failure is visible.

Original transactions are append-only. Normalisation during ingest does not
change them later, and analysis does not change them either.
