# Suspicious pattern detection

Method `indicators.v1`. Each fired row is `assertion_kind=inferred`. The
limitations always include:

`Verified edges only. Narration-derived links were excluded. This is a rule match.`

Thresholds are stored on the run. The defaults are demonstration settings, not
legal thresholds: fan-in 3, fan-out 3, pass-through ratio `0.85`, dwell 24
hours, amount floor `1000.0000`, currency INR.

## Edges that count

A row counts only when `counterparty_resolution` is `structured_field`, the
currency matches the run, and the booking date is inside the window. A debit
and a credit with the same reference, amount, currency, and swapped accounts
are one edge. Fan-in support prefers the credit id when the credit exists.
Fan-out support prefers the debit id.

## Codes

| Code | Fires when |
| --- | --- |
| `FAN_IN` | Distinct verified sources into the account are at least `fan_in_min`. |
| `FAN_OUT` | Distinct verified destinations from the account are at least `fan_out_min`. |
| `PASS_THROUGH` | Verified inflow and outflow both exceed `amount_floor`, and outflow/inflow is at least the ratio. |

Inflow and outflow for `PASS_THROUGH` are sums of those verified edges. They
are not a FIFO allocation. The limitation says so.

Dwell runs only when every supporting row has `time_precision=time`. The rule
then requires the latest outflow clock to be at or after the earliest inflow
clock, and the span to be within the dwell hours. If any supporting row is
date-only, dwell is not applied and the limitation says that. A span longer
than the dwell does not fire. An outflow clock before the inflow clock does
not fire.

Copy is "rule matched". It is not "mule".

## Evaluated and not shipped

| Requested pattern | Result in this release |
| --- | --- |
| Circular transactions | Visible as statement hops when both legs exist. No `CYCLE` code. ADR 0015. |
| Rapid movement | No score. The trace response includes `hours_after_previous` when both hops have clocks, otherwise null. |
| Structuring | Not implemented. No reporting threshold is configured. |
| Dormant then active | Not implemented. Activity text says no baseline is stored. |
| Shared counterparty as a network | Not inferred. Fan-in lists the counterparties that matched the count. It does not say they know each other. |

`POST /api/v1/cases/{case_id}/indicator-runs` stores one finding per fired
row. If nothing fires, one finding says no rule matched and that this is not
a finding of legitimate activity. `GET /api/v1/cases/{case_id}/indicators`
returns the latest succeeded run.
