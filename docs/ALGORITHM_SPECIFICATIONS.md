# Algorithm specifications

Phase 1 runs three methods: `fifo.v1`, `indicators.v1`, and `correlate.v1`.
They are deterministic. They do not learn. A numeric confidence is not an
output. Support is a list of evidence ids plus an assertion kind.

## How the requested labels map onto the approved kinds

ADR 0006 allows `verified`, `inferred`, and `hypothesis` only.

| Word in the request | Representation in VAGEXA |
| --- | --- |
| Directly supported | `assertion_kind=verified`. A cited source field states the claim. |
| Corroborated | Still `verified` or still `inferred`. The finding lists two or more independent evidence ids. The count is not a probability. |
| Inferred | `assertion_kind=inferred`. A named method produced the claim from verified inputs. |
| Hypothetical | `assertion_kind=hypothesis`. |
| Unresolved | No relationship row, a `proposed` row not yet decided, or a `trace_residual`. |
| Contradicted | Two observations or two proposals both kept. Neither is deleted and neither is averaged. |

Confirm changes `status` only.

## `fifo.v1`

### Input

```json
{
  "case_id": "uuid",
  "seed_transaction_ids": ["uuid"],
  "max_layer": 3,
  "currency": "INR"
}
```

Seeds are current transactions in the case. `max_layer` is 1 to 5. Default 3.

### Output

`trace_flows`, `trace_residuals`, and one finding. Amounts are decimals.
`output_hash` is SHA-256 of the canonical JSON of flows and residuals.

### Description

1. Load current transactions for every account that appears as a statement subject or a structured counterparty in the case.
2. Sort by `booking_date`, `booking_time` nulls last, `line_number`, `id`.
3. Net a credit against an earlier debit only when `reference_raw` is non-empty and equal, the currency matches, and the credit is less than or equal to the unmatched remainder. Method name `reversal_reference`.
4. Each account has a queue of lots: amount, currency, origin complaint, layer arrived.
5. A seed credit, or a seed debit's counterparty credit when both sides exist, enqueues a lot at layer 0 for the receiving account. The first emitted hop is layer 1.
6. An outgoing debit dequeues the oldest lots of that currency and emits one flow per lot consumed, with `layer_to` equal to the lot's arrival layer plus one.
7. Stop enqueueing onward lots when `layer_to` would exceed `max_layer`. The remainder is a residual `outside_horizon` on the account that still holds it.
8. A cash debit emits `exit_kind=cash` and a null destination.
9. A named destination with no statement of its own emits the flow and a residual `no_onward_record` on that destination.
10. Unrelated credits are not given a complaint id.
11. Per account, currency, and complaint, attributed outflow must be at most attributed inflow, within `0.01`, counting a seed credited there as inflow. Do not sum hop amounts and compare the total with the seed. On failure, status `failed` and no flows are published.

### Complexity

Sort is O(T log T). The scan is O(T) lot operations for a few thousand rows.
The case bound in the technology note is a few thousand transactions. That
fits the 10-second CI target once the fixture exists.

### Limitations

The result is where value sits inside the supplied statements under this
policy. A missing statement ends the path. Date-only order is file order, and
the finding says so. Horizon 3 does not attribute a fourth hop.

### Example

Synthetic fixture, seed the victim debit of `100000.0000` from
`100000000001`, `max_layer` 3. Flows: V→I1, I1→I2, I2→I3, each `100000.0000`.
Residual on I3: `100000.0000`, `outside_horizon`. Account `100000000019` is
not a flow destination. The sum of the three flow amounts is `300000` and
must not be compared with `100000`.

### Tests

- That example, including the residual and the absence of an attributed edge to B.
- The same input run twice has the same `output_hash`.
- Two same-day rows with null times follow line number.
- A reversal with the same reference nets. A different reference does not.
- A debit larger than the attributed balance emits only the attributed part.
- A conservation fault (a test double that emits an extra amount) fails the run.
- A seed from another case is rejected.

## `indicators.v1`

### Input

```json
{
  "case_id": "uuid",
  "window_start": "2026-01-15",
  "window_end": "2026-01-16",
  "fan_in_min": 3,
  "fan_out_min": 3,
  "pass_through_ratio": "0.85",
  "pass_through_dwell_hours": 24,
  "amount_floor": "1000.0000",
  "currency": "INR"
}
```

These defaults are parameters stored on the run. They are not legal thresholds.

### Output

Zero or more `account_indicators`. Each has `support_transaction_ids`,
`assertion_kind=inferred`, and non-empty `limitations`.

### Description

Build verified transfer endpoints from current transactions whose
`counterparty_resolution` is `structured_field` and whose booking date is
inside the window. Group by account.

- `FAN_IN`: distinct counterparties on credits `>= fan_in_min`.
- `FAN_OUT`: distinct counterparties on debits `>= fan_out_min`.
- `PASS_THROUGH`: attributed or verified inflow and outflow both exceed
  `amount_floor`, and outflow/inflow `>= pass_through_ratio`. Apply the dwell
  test only when every supporting row has `time_precision=time`. Otherwise
  omit dwell and write that sentence into `limitations`.

Narration-pattern edges are not counted. The limitation says they were
excluded even when the count is zero and the code does not fire. A fired row
still says it.

The copy is "rule matched". It is not "mule" and not a probability.

### Complexity

One pass over the verified edges in the window. O(E).

### Limitations

Structured fields only. A narration-only mule pattern will not fire. That is
the approved choice. Thresholds are demonstration settings.

### Example

Three verified credits of `20000.0000` into `100000000030` fire `FAN_IN`
with three support ids. Four verified debits from that account fire `FAN_OUT`.

### Tests

- Fan-in at 3 fires. At 2 it does not.
- An inferred narration edge does not increase the count, and the limitation mentions the exclusion.
- Date-only pass-through does not claim a 24-hour dwell.
- Support ids are all in the case.

## `correlate.v1`

### Input

The current accounts, complaints, domains, DNS observations, and hosting
notes of one case, plus a SQL equality lookup for the same normalised account
key or domain name in other cases. The lookup returns counts, not narratives.

### Output

Proposed `relationships` in this case, and a signal list for other cases.
Overlap rows include this limitation, stored verbatim:

"Shared hosting, a shared address, or shared DNS does not establish common ownership, common control, or a common operator."

### Description

| Signal | `rel_type` | Kind | Status |
| --- | --- | --- | --- |
| Exact host contained in the stored complaint text | `mentioned_in` | `verified` for containment | `proposed` |
| Two observations in the case name the same IP | `infrastructure_overlap` | `verified` for co-occurrence | `proposed` |
| Same domain name in another case | `shared_domain_name` | `inferred` as "the same name was recorded" | Not a stored cross-case row. A signal. |
| Same account number and IFSC in another case | Signal only | `inferred` as co-occurrence of the key | Count and masked id |

No party is created. Name similarity is not run in Phase 1.
Absence of a signal creates nothing.

### Complexity

Equality lookups on the unique indexes. O(keys in the case).

### Limitations

A shared IP is not control. A shared account number can still be a repeated
typo. The signal says the keys match. It does not say the holders match.

### Example

`syn-a.test` and `syn-b.test` both observed at `203.0.113.50`. One overlap
relationship. Two holder names on `100000000011` produce two observations and
zero parties.

### Tests

- Overlap limitation text is exact.
- No `parties` insert.
- Caller assigned to one case receives `other_case_count` and not the other title.
- Analyst confirm returns 403.

## Evaluated and not implemented in Phase 1

| Method | Why it is not in this release |
| --- | --- |
| Cycle finder | The hop cap stops the walk. A `CYCLE` label is finding M01 and is deferred. The edges of a return are still visible if both statements exist. |
| Payments per day, as a score | A frequency can be read off the transaction list. A score has no baseline and no approved threshold. |
| Degree or betweenness centrality | It ranks accounts. The investigator did not ask for a ranking, and the approved scope excludes it. |
| Community detection | Phase 2 at the earliest, and the result would be a component label, not a criminal network. Phase 1 returns weakly connected components only. |
| A learned classifier | No training set, no objective that is not already a rule, and no evaluation set that is separate from the fixture. |

## Copilot tools

Each tool is a function. The request names it. Optional question text is
stored and ignored by selection.

| Tool | Returns |
| --- | --- |
| `summarize_case` | Counts, classification, whether a succeeded trace exists |
| `trace_summary` | Latest succeeded trace: layers, amounts, residuals, evidence ids. Reason `no_successful_trace` when none. |
| `list_indicators` | Codes, thresholds, support ids, limitations |
| `common_beneficiaries` | Exact shared account keys inside this case and their complaint or transaction ids |
| `infrastructure_for_case` | Observations with times and the overlap limitation when an overlap exists |
| `list_evidence` | Evidence rows for ids that this response already holds |

A tool that lacks data returns an empty list and a reason code. It does not
fill the gap.
