# 0014. Owner decisions after the architecture audit

- Status: accepted
- Date: 2026-11-22

## Context

The architecture audit left four product choices open: which edges fan-in and
fan-out count, whether the default horizon should show a four-hop beneficiary,
whether a global administrator may read case narratives, and whether Phase 1
routes free-text questions onto tools. Those choices change authorisation,
tests, and the copilot contract. They were put to the owner rather than guessed.

## Decision

`FAN_IN` and `FAN_OUT` count verified edges only. Edges inferred from a
narration stay on the graph with their own assertion kind and are excluded
from the count. The indicator says so.

The default horizon remains 3, and the hard cap remains 5. The synthetic
chain in the data validation report, with three intermediaries and a further
beneficiary, is the fixture. Under horizon 3 that last account is an
`outside_horizon` residual. The interface and the report use the residual
reason. They do not call that account the beneficiary the policy attributed.

A global administrator does not gain read access by the role alone. Narratives,
statements, and transactions require assignment to the case, including for an
administrator. The administrator role still manages users and assignments.
Inside a case, the assignment role limits the action: an analyst may run a
trace and may not confirm a relationship.

Phase 1 copilot calls take a tool name from the allow-list. Optional question
text is stored on `copilot_queries` and is not interpreted as a tool selector.
Keyword routing is not part of this phase. An LLM remains off by default.

## Consequences

- `FR-ACC-03` and `FR-AI-01` match this record.
- The authorisation test for increment 1A includes an unassigned administrator
  and expects 404.
- The golden trace asserts a residual, not a layer-4 attribution, at the
  default horizon.

## Alternatives

- Count inferred narration edges. Finds more structure and weakens the
  verified count. Not selected.
- Raise the default horizon to 4. Shows the last account inside the policy
  and hides the horizon lesson. Not selected.
- Give administrators a global narrative read. Conflicts with the product
  vision. Not selected.
- Route free text with keywords. Brittle, and unnecessary for the tools.
  Not selected.
