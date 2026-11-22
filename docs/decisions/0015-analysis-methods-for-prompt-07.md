# 0015. Analysis methods for the financial intelligence prompt

- Status: accepted
- Date: 2026-11-22

## Context

Prompt 07 asked for cycle detection, rapid-movement detection, structuring-like
detection, dormant-to-active detection, backward fund allocation, and a
separated risk score. The accepted algorithm specification already defers a
cycle label, a frequency score, centrality, community detection, and a learned
classifier. `FINANCIAL_INTELLIGENCE.md` keeps structuring for a later method
version. ADR 0007 allows one allocation policy, `fifo.v1`.

## Decision

This change implements `fifo.v1`, `indicators.v1` (`FAN_IN`, `FAN_OUT`,
`PASS_THROUGH`), and account activity measured from statement rows.

It also adds `statement_walk.v1`. That method lists observed structured-field
hops forward or backward. It does not allocate value, does not write
`trace_flows`, and does not emit a `CYCLE` indicator. A path that would return
to an earlier account stops and records `returned_to_earlier_account`. The
finding assertion kind is `hypothesis`.

These are not implemented, and they are not hidden inside another code:

- a `CYCLE` indicator
- a rapid-movement score
- a structuring rule, because no reporting threshold is approved
- a dormant-to-active rule, because no baseline period is stored
- a second allocation policy
- one number that mixes severity, confidence, evidence quality, and priority

There is no risk-score table. A finding keeps its method, version, assertion
kind, limitations, and support evidence ids separate.

Runs finish inside the request. The `jobs` row is written already completed.
A later worker can call the same functions. `analytical_runs.output` stores the
observed-sequence payload. FIFO results stay in `trace_flows` and
`trace_residuals`. `complaint_id` is nullable and has no foreign key until a
complaints table exists.

## Consequences

- The synthetic chain is the FIFO fixture. Horizon 3 leaves account B as
  `outside_horizon`.
- Indicator copy says the rule matched. It does not say mule.
- A graph screen is still a later milestone. This decision does not draw one.

## Alternatives

- Implement every requested detector and a blended score. That would reverse
  the accepted algorithm specification inside one change. Rejected.
- Treat the statement walk as FIFO in reverse. That is a second allocation
  policy. Rejected.
