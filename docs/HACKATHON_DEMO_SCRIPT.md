# Hackathon demonstration script

About four and a half minutes. One case, `SYN-DEMO`. Sign in as the seeded
investigator, then use **Start the guided walkthrough** on the dashboard.
The in-app guide has nine short steps. This script is the eight things to say.
If a click fails, use the backup on that step. Do not upload a file.

Say "synthetic" once at the start. Do not say that anyone committed an
offence, and do not name an operator.

## Step 1 — Introduce the investigation (30 seconds)

Open the dashboard. The demonstration card shows `SYN-DEMO`, the synthetic
badge, and the objective in the title. Select **Open the investigation**.

Expected: 25 transactions, 14 statements, 3 gateway records, a `fifo.v1`
trace with 3 hops, and a residual of ₹1,00,000.00 on `****0013` marked
`outside_horizon`. The banner says the records are fictional.

Say: the objective is to see which stored records connect a merchant payment
to later transfers, and which links stay unresolved.

Backup: the same figures are on the card before the case is opened.

## Step 2 — Reveal the financial trail (45 seconds)

Open **Financial**, or follow the guide to the opening payment and then to
fund flow. The selected debit is `DEMO-V-1`: `****0001` to `****0011`,
₹1,00,000.00, reference `UTRSYN0001`, booked 2026-01-15 09:00.

Expected on the flow view: `****0001` → `****0011` → `****0012` → `****0013`.
The residual stays on `****0013`. `****0019` is not in the allocation.

Say: three hops are allocated from the opening debit. The next statement
debit is visible as a statement, and it is not called the beneficiary.

Backup: the case overview states the same residual without the flow diagram.

## Step 3 — Explain the pattern findings (30 seconds)

Open **Financial** with the findings view, or the guide step "Pattern findings".

Expected: `FAN_IN` and `FAN_OUT` on `****0030`, `indicators.v1`, inferred,
with the rule-match limitation. No pass-through row.

Say: three accounts paid in and the same account paid four amounts out. That
is a rule match on the supplied window, not a finding of guilt. The ordinary
account `****0060` did not match.

Backup: the overview lists the same two rule names.

## Step 4 — Explore the infrastructure (30 seconds)

Open **Infrastructure**. Select `syn-a.test`.

Expected: A `203.0.113.50` observed 2026-01-14 10:00 UTC, and A
`203.0.113.60` observed 2026-01-20 10:00 UTC. `syn-b.test` shows the same
first address. The overlap is unresolved. The limitation says shared hosting
or a shared address does not establish a common operator.

Say: both DNS answers are kept. The shared address is co-occurrence.

Backup: the report's infrastructure table lists the same rows.

## Step 5 — Show the bridge, and the disagreement (45 seconds)

Open **Unified intelligence**. The selected row should be the corroborated
gateway link, `****0011` to `syn-a.test`, status proposed.

Expected support: gateway record `SYN-PG-0001` and the `UTRSYN0001` statement
rows. A second list entry is the narration link from `****0001`. Further down,
`****0071` to `syn-d.test` and `****0071` to `syn-e.test` are contradicted.
`syn-a.test` with `syn-b.test` is unresolved.

Say: the gateway record and the narration agree on `syn-a.test`. Two later
gateway records name different hosts for one payment, and both are still
stored. Agreement is not ownership. Disagreement is not deleted.

Backup: search `UTRSYN0001` in the evidence list if the row is not selected.

## Step 6 — Open the network (40 seconds)

Open **Network**. The guide selects the corroborated gateway edge.

Expected: the opening transfer runs from `****0001` toward `****0013`, the
gateway edge reaches `syn-a.test`, and `syn-b.test` meets it only through the
shared address. The `2500.00` edge from `****0070` to `****0071` is separate.

Say: the graph is the same rows as the lists. Direction and amount come from
the statements. The shared address is not an ownership edge.

Backup: if the canvas is empty, stay on Unified intelligence. The edges are
listed there with the same classifications.

## Step 7 — Open the source records (30 seconds)

Open **Evidence**. The guide selects `SYN-PG-0001`.

Expected: source `synthetic_payment_gateway`, merchant `syn-a.test`,
settlement account `****0011`, amount ₹1,00,000.00, synthetic label, and a
collection time. Open `DEMO-V-1` and show the narration. Then point at
`SYN-PG-0090` and `SYN-PG-0091` without choosing between them.

Say: this is the stored synthetic record. It supports the link that the
fields state. It does not identify an operator.

Backup: the relationship evidence panel lists the same objects.

## Step 8 — Close on the report (25 seconds)

Open **Report**.

Expected: the same counts, the three allocated hops, the residual, the two
indicator lines, the DNS table, the corroborated link, the two contradicted
links, the unresolved overlaps, and the limitations. Print is available. The
report does not add a relationship that is absent from the evidence list.

Say: observed records and analytical results are separate. The open questions
are the residual after the horizon, the unresolved shared infrastructure, and
the contradicted gateway records.

Backup: read the overview narrative. It is built from the same summary.
