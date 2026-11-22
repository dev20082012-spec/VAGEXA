# 0007. FIFO is the default tracing policy

- Status: accepted
- Date: 2026-11-22

## Context

When an account receives money from more than one source and pays it onward,
the system must say which inbound value the outbound payment carries. That
choice changes the picture. Leaving it implicit would make two runs
incomparable.

FIFO spends the oldest attributed lots first. It is explainable on a timeline
an investigator can audit. Pro-rata splits every outbound payment in proportion
to the balance and answers a different question. Tainted-first chasing
maximises onward attribution and overstates how far a complaint's money went.

## Decision

The default policy is `fifo` version `fifo.v1`, horizon 3, hard cap 5.
Parameters are stored on the analytical run. Pro-rata may be added as an
explicit policy in Phase 2. It is not an automatic fallback. There is no
tainted-first policy in the roadmap unless a later ADR adds one and the report
describes the bias.

Unattributed credits are not given a complaint's identity to make the graph
complete.

## Consequences

- The synthetic scenario must pin expected FIFO amounts.
- The UI shows the policy name on the graph that came from a trace.
- A change to allocation rules changes the version string.
- The conservation formula and the row order are specified in ADR 0010. They are not a reversal of FIFO.

## Alternatives

- Pro-rata as the default. Defensible and harder to explain row by row.
  Deferred as an optional policy.
- Last-in-first-out. No investigative reason to prefer it. Rejected.
- A learned model that allocates value. Not explainable enough for evidence.
  Rejected.
