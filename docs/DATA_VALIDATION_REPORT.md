# Data validation report

Date: 2026-11-22. This report checks the data model against investigation
facts, then walks six synthetic scenarios. Every account number, name, domain,
and amount below is invented. None of it is a real customer's record, and none
of it is ground truth loaded into an investigator view.

The model described here is the model after the corrections in
[Architecture audit](ARCHITECTURE_AUDIT.md) C01–C08. Where a scenario still
fails, the failure is an open finding, not a silent fix.

## What the corrected model can represent

| Fact | Where it lives | Lineage |
| --- | --- | --- |
| Several investigations | `cases`, each `official` or `synthetic`, never both | `created_by`, `created_at` |
| An account number or VPA | `accounts`, immutable normalised key | Created on first sight inside that database |
| A printed holder name | `account_observations`, many per instrument, append-only | `case_id`, `statement_id`, `provenance_id` |
| A statement and its rows | `source_files` bytes, `statements`, `transactions` | File hash, line number, parser version |
| A newer parse of the same bytes | New `statements` row with `supersedes_statement_id` | Old transactions remain and drop out of analytical queries |
| A hop chain | `trace_flows` tied to one `analytical_runs` row | Method version, sort order, seeds, source transaction |
| A complaint | `complaints` | Provenance. Structured subject account is still only via seeds or relationships |
| A domain, IP, DNS answer | `domain_names`, `ip_addresses`, `dns_observations` | Observation time, resolver, provenance |
| The same instrument in two cases | Same `accounts.id`, different observations and different case links | Cross-case read is a count, not a shared narrative |
| Verified, inferred, hypothesis | `assertion_kind` on the row that makes the claim | Distinct from `relationships.status` |
| A limitation | Required text on findings and on overlap rows | Not a probability of guilt |
| An analyst decision | `relationships` status fields plus an audit event; `resolution_decisions` | Does not edit the source row |
| An audit event | `audit_events`, insert-only | Actor, action, outcome, request id |

## What it still cannot represent cleanly

- A numeric confidence. The model refuses a guilt probability. Method name and assertion kind are the explanation. Whether to add a separate method-strength label is not decided.
- An analyst sticky note (finding M04).
- A certificate or a WHOIS record (finding M05). DNS and hosting rows must not be overloaded.
- A wallet (finding L01).
- A parent domain (finding M09).
- A cycle label (finding M01). The edges can exist; the label does not.
- Two classifications on one instrument inside one database. Separation is by database, not by a column on a shared key. That is intentional. A restore of a demo dump into the operational database is still an operational failure, not something the unique key can see across servers.
- Foreign keys on polymorphic relationship ends (finding M02).

## Identifiers, uniqueness, and indexes

Instrument uniqueness, partial:

- `(account_number_norm, ifsc_norm)` where both are present.
- `(vpa_norm)` where present.
- `domain_names.name_norm`.
- `ip_addresses.address`.

These unique keys are safe only because one deployment database is one data
mode. They are not a theory of legal identity.

Required foreign keys, the ones the database can actually enforce:

- observations, statements, transactions, runs, flows, and complaints reference `cases`.
- transactions reference `statements`.
- `counterparty_account_id` and observation `account_id` reference `accounts`.
- flows reference `analytical_runs` and `transactions`.
- evidence references provenance.

Not enforceable with a single foreign key: `relationships.from_id` and `to_id`.
The write path must check the kind. Tests should insert an unknown id and
expect a rejection.

Indexes the first migration should create beyond the unique keys:

- `transactions (case_id, booking_date, booking_time, line_number)` so FIFO's order is the index order.
- `account_observations (case_id, account_id)`.
- `relationships (case_id, status)`.
- `dns_observations (domain_id, observed_at)`.
- `jobs (status, created_at)`.

`gen_random_uuid()` is fine. It must not be the FIFO tie-break ahead of line number. ADR 0010 puts the transaction id last, after line number, so two rows in one file do not depend on UUID ordering for their sequence. UUID order is only the final tie if line numbers collide, which the unique `(statement_id, line_number)` forbids inside one statement.

## Worked scenarios

All of the following are synthetic. IFSC `SYNB0000001` and the account numbers
are placeholders. `203.0.113.50` is inside the documentation range and is not
an address to look up for a real investigation.

### Scenario 1 — mule chain

Three intermediary accounts, then a final beneficiary. That is four hops from
the victim, not three.

Input, each line on the statement of the subject account, currency INR,
booking date 2026-01-15:

| Subject | Time | Direction | Amount | Counterparty | Reference |
| --- | --- | --- | --- | --- | --- |
| 100000000001 (V) | 09:00:00 | debit | 100000.0000 | 100000000011 (I1) | UTRSYN0001 |
| 100000000011 (I1) | 09:01:00 | credit | 100000.0000 | 100000000001 | UTRSYN0001 |
| 100000000011 (I1) | 09:20:00 | debit | 100000.0000 | 100000000012 (I2) | UTRSYN0002 |
| 100000000012 (I2) | 09:21:00 | credit | 100000.0000 | 100000000011 | UTRSYN0002 |
| 100000000012 (I2) | 10:00:00 | debit | 100000.0000 | 100000000013 (I3) | UTRSYN0003 |
| 100000000013 (I3) | 10:01:00 | credit | 100000.0000 | 100000000012 | UTRSYN0003 |
| 100000000013 (I3) | 11:00:00 | debit | 100000.0000 | 100000000019 (B) | UTRSYN0004 |
| 100000000019 (B) | 11:01:00 | credit | 100000.0000 | 100000000013 | UTRSYN0004 |

The victim statement alone can show V to I1. It cannot show I2, I3, or B.
Those appear only because their statements were supplied. That limit is a
result, not a defect to paper over.

Expected result under `fifo.v1` with `max_layer` 4: attributed flows V→I1
(layer 1), I1→I2 (layer 2), I2→I3 (layer 3), I3→B (layer 4), each
`100000.0000`, each `verified` where both structured references match, method
`reference_join`. Per-account conservation holds. The sum of the four flow
amounts is 400000 and must not be checked against the seed of 100000.

Expected result under the default horizon of 3: the same flows through I3, and
a residual of `100000.0000` on I3 with reason `outside_horizon`. B is not
attributed.

Evidence: the eight transaction rows, the file hashes, and the run parameters.

Can be concluded: under the stated policy and the supplied statements, the
seeded amount is attributable along those hops.

Cannot be concluded: that any holder is a mule, that the path is the only path
in the world, or that B received the money when the horizon was 3 and the
residual was ignored.

Analyst view: a layer list plus a residual panel. The residual panel is empty
only when the horizon actually covered the path. The graph shows statement
edges even before the trace, and FIFO edges only after the run, with the
policy name on the FIFO edges.

### Scenario 2 — fan-in

Three subject accounts, A1 `100000000021`, A2 `100000000022`, A3
`100000000023`, each debit `20000.0000` to C `100000000030` on 2026-01-16,
with structured counterparty fields. C's statement shows the three credits.

Expected result: fan-in count 3 on verified edges. With the documented
demonstration threshold of 3, `FAN_IN` fires, assertion `inferred`, support
ids are the three credits (or the three debits, and the method must say
which). Method `indicators.v1`.

Can be concluded: three supplied accounts sent the stated amounts to C inside
the window.

Cannot be concluded: that C is a collection mule, or that the senders know
each other.

Analyst view: the indicator row lists the threshold, the count, and links to
the three transactions. The copy says the rule matched.

### Scenario 3 — fan-out

C debits `10000.0000` each to D1–D4, structured counterparties, times within
the same window.

Expected result: fan-out count 4, `FAN_OUT` fires. If C's credits from
scenario 2 and these debits are in one window and the ratio meets `0.85`,
`PASS_THROUGH` can also fire. It must cite both the inflow ids and the outflow
ids. If the times are dates without clocks, dwell is not evaluated (C08's
sibling rule, H10).

Can be concluded: C paid four destinations in the supplied statement.

Cannot be concluded: that the destinations are a network of offenders.

Analyst view: the four edges on the graph, assertion `verified` for the
structured fields, and the indicator beside them rather than instead of them.

### Scenario 4 — cross-case relationship

Case SYN-A and case SYN-B both contain instrument `(100000000011, SYNB0000001)`.
The caller is assigned to SYN-A only.

Expected result: a signal `{ kind: account, masked: "****0011", other_case_count: 1, assertion_kind: inferred, method: exact_identifier }`. No title, narrative, or transaction from SYN-B.

Evidence: the two observations or transaction rows that carry the normalised key. The signal is computed, not a global relationship row (C06).

Can be concluded: the same normalised account number and IFSC occur in another case the caller cannot open.

Cannot be concluded: that the holders are the same person, that the cases are one scheme, or what the other case is about.

Analyst view: a count and a masked key on the SYN-A screen. Opening SYN-B fails with 404.

A second user assigned to both cases may open both. The screen may then show the identifier in each case. It still does not show a control finding.

### Scenario 5 — infrastructure overlap

On SYN-A, an observation records that `syn-a.test` resolved to `203.0.113.50`
at 2026-01-16T09:00:00Z. On SYN-B, `syn-b.test` resolved to the same address at
2026-01-16T09:05:00Z. Both observations are `public_intelligence` if they came
from a resolver, or `unverified` if an investigator typed them. The scenario
should use typed observations so the demo does not depend on the public DNS.

Expected result: an overlap record whose claim is only "these observations
name the same IP". Assertion `verified` for that sentence. Limitation text
includes that shared hosting, a shared address, or shared DNS does not
establish common ownership, common control, or a common operator.

Can be concluded: the stored observations contain the same address.

Cannot be concluded: that the domains share an owner, a customer, or a crime.
A later certificate or RDAP row would be another observation, still not
ownership, unless the source field itself states a registrant, and even then
the registrant is a registrar's assertion about a name, not a finding that the
registrant committed the fraud.

Analyst view: two domain nodes, one IP node, two `resolves_to` edges with
times, and the limitation in the edge inspector. No party node is created.

### Scenario 6 — evidence conflict

Statement file F1, hash recorded, says the holder printed for
`100000000011` is `SYN NAME ONE`. Statement file F2 says the holder printed
for the same number and IFSC is `SYN NAME TWO`.

Expected result: one instrument row and two `account_observations`. Neither
name is updated away. No `same_as` and no party merge. A hypothesis
`possible_same_party` is not created from the name difference. The names
differ, so they are not a name-similarity merge either. They are a conflict on
one instrument.

Can be concluded: two supplied files attribute two printed names to one
normalised number.

Cannot be concluded: which name is true, or that either person controls the
account.

Analyst view: the account panel lists both observations with file hashes and
parser versions. Nothing is pre-selected.

The pre-audit table could store only one `holder_name_raw`. This scenario is
why that column was removed as the source of truth.

## Fixture consequence

ADR 0014 adopts these tables as the synthetic fixture. Scenario 1's account B
is outside the default horizon. A test that expects B at layer 3 is testing a
different policy. The accepted assertion is a residual on I3 with reason
`outside_horizon`, shown as a residual and not as the attributed beneficiary.
