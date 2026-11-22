# Financial intelligence

This engine turns statement files into canonical transactions, attributes value
across a short hop chain, and raises explainable indicators. It is implemented
as pure functions plus repositories. HTTP and the React client call it. They
do not reimplement it.

The policy choices are [ADR 0007](decisions/0007-fifo-tracing-policy.md).

## Scope of the first parser

The organiser's sample layout is not published in enough detail to hard-code a
bank format. The canonical CSV is the contract. A later bank or sample file
gets its own parser that emits the same canonical rows.

Required CSV columns:

| Column | Rule |
| --- | --- |
| `line_number` | Stable row identity inside the file. |
| `booking_date` | ISO date. |
| `booking_time` | Optional `HH:MM:SS`. Empty means precision `date`. |
| `direction` | `debit` or `credit`. |
| `amount` | Decimal string, positive, at most four decimal places. |
| `currency` | ISO 4217, typically `INR`. |
| `rail` | `upi`, `imps`, `neft`, `rtgs`, `cash`, `cheque`, `card`, `internal`, `unknown`. |
| `narration` | Raw text, may be empty. |
| `counterparty_account` | Optional. |
| `counterparty_ifsc` | Optional. Required when a bank account number is set. |
| `counterparty_vpa` | Optional. |
| `reference` | Optional UTR, RRN, or bank reference. |
| `balance_after` | Optional decimal. |
| `subject_account` | Required, on the upload rather than on every row. Account number plus IFSC, or a VPA. Identifies whose statement this file is. |

The original file is kept even when it is also valid CSV. The parser version is
stored on the statement. Unknown columns are ignored and listed in the job
result so a mapping gap is visible.

PDF and HTML statements are a later parser behind the same interface. They are
not scraped with an ad hoc expression inside the upload route.

## Canonical transaction

A transaction is one posted leg on one statement. It is not yet a transfer.
Two legs form a stronger transfer when a rule joins them. Until then, the
counterparty may be unresolved.

Rails cover the Indian retail paths investigators actually see: UPI, IMPS,
NEFT, RTGS, cash, cheque, card, and internal transfers. Anything else is
`unknown`, which is a valid state.

Extraction of a VPA or UTR from narration uses `narration_extractor` with a
version. The first version may recognise a single obvious VPA token
(`local@handle`) and a labelled UTR/RRN. A bare digit run is not an account
number. The extractor returns a candidate or nothing.

## Seeds

A seed is a transaction an investigator has confirmed, optionally tied to a
complaint. The engine may propose candidates when a complaint states an amount,
a currency, and a date window, and exactly those fields match a credit. That
proposal is a hypothesis list. It is not a seed.

If several rows match, the investigator chooses. The system does not pick the
closest one.

## Layers

Layers are properties of value in one trace run.

| Layer | Definition |
| --- | --- |
| 0 | The seeded source side. Often the victim account that sent funds. |
| 1 | The account that received the seeded value. |
| 2 | An account that received onward attributed value from a layer-1 account. |
| 3 | The next onward account. |

The default horizon is layer 3. A request may ask for fewer hops. It may not
ask for more than 5. An account can be layer 1 in one complaint and layer 2 in
another. The layer is stored on `trace_flows.layer_to`, never as a permanent
column on `accounts`.

## FIFO allocation

Default method: `fifo`, version `fifo.v1`. Row order is `booking_date`, then
`booking_time` with nulls last, then `line_number`, then transaction id.
ADR 0010. Date-only rows therefore follow file order, and the run records that
this is not clock order.

Model each account as a queue of lots. A lot is an amount, a currency, an
origin complaint when known, and the layer at which it arrived. Incoming
attributed value enqueues a lot. An outgoing debit dequeues the oldest lots
first and emits one `trace_flow` per lot consumed, with the consumed amount.

Rules:

- Only value that entered through a seed, or through an already attributed
  inflow, is allocated onward. Unrelated credits stay in the account as
  unattributed and are not given a victim's identity.
- A debit larger than the attributed balance emits a flow only for the
  attributed part. The remainder of that debit is not labelled with the complaint.
- Lots do not cross currencies.
- The horizon stops further enqueue. Value still sitting in the last layer is
  a residual with reason `outside_horizon`.
- A cash rail debit consumes lots and emits a flow with `from_account_id` set,
  `to_account_id` null, and `exit_kind = cash`. No account is invented.
- When the destination account's own statement is not in the case, the flow
  still records the destination if the source row named it, and the residual
  reason on that destination is `no_onward_record`.
- A credit nets against an earlier debit only when the reference is non-empty
  and exactly equal, the currency matches, and the credit amount is less than
  or equal to the unmatched remainder. The method name is
  `reversal_reference`. Every other credit stays a credit.

Conservation is per account, currency, and complaint: attributed outflow is at
most attributed inflow at that account, within `0.01`, counting a seed credited
there as inflow. The sum of flow amounts across layers is not compared with
the seed. A 100 amount that passes three hops emits three flows and still
conserves. On violation the run status is `failed` and flows are not published.

The same inputs and the same `fifo.v1` parameters produce the same flows. Tests
pin that with the synthetic scenario.

## Pro-rata

`prorata` is a different policy. It splits each debit in proportion to the
attributed and unattributed balance at that moment. It is not a fallback when
FIFO is inconvenient. Selecting it is an explicit parameter on a new run, with
its own version, and the report names it. Implementation is Phase 2.

## Joining two statements

| Situation | Assertion | Method |
| --- | --- | --- |
| Both statements contain the leg and the reference matches | `verified` | `reference_join` |
| One statement has a structured counterparty account and IFSC | `verified` | `structured_counterparty` |
| One statement yields one unambiguous VPA from the versioned extractor | `inferred` | `narration_extractor` |
| Amount and date window match and no identifier matches | `inferred` only if an investigator confirms the candidate as a seed or a link | `amount_time_window` |
| Holder names are similar | `hypothesis` | `name_similarity` |

Amount-and-time matches are not auto-confirmed. Name similarity never allocates
money.

## Fan-in and fan-out

Computed on `verified` transfer endpoints in a window the run records:

- fan-in: distinct source accounts;
- fan-out: distinct destination accounts;
- the sums of those amounts, as decimals.

The window and the minimum count are parameters of `indicators.v1`, stored on
the run. They are not constants hidden in the UI.

These counts use `verified` edges only. Narration-derived links are excluded,
and the indicator text says they were excluded. The graph still draws those
links with their own assertion kind. ADR 0014.

## Indicators in `indicators.v1`

Each indicator row cites `support_transaction_ids` and a limitation string.
The assertion kind is `inferred`. The copy says the rule matched. It does not
say the account holder committed an offence.

| Code | Fires when, under the run's thresholds |
| --- | --- |
| `FAN_IN` | Distinct verified sources in the window are at least the configured count. |
| `FAN_OUT` | Distinct verified destinations in the window are at least the configured count. |
| `PASS_THROUGH` | Attributed inflow and onward outflow both exceed the amount floor, and the onward share of inflow is at least the configured ratio. The dwell test runs only when both sides have `time_precision = time`. If either side is date-only, dwell is not applied and the limitation says so. |

Default demonstration thresholds, stored explicitly so a test can change them:
fan-in count 3, fan-out count 3, pass-through ratio `0.85`, dwell 24 hours,
amount floor `1000.00` INR. These are analytical settings, not legal thresholds.
The report prints them.

Round-amount clusters, night bursts, and structuring rules are later codes in a
later method version. They are not implied by a silent score.

## Coverage

Every trace result includes:

- seeded amount;
- amount allocated at each layer;
- residual amount and reason;
- count of unresolved counterparties;
- the statement ids that were in scope.

"Where the money is" means "where it is inside the supplied statements under
this policy". The result says that in the limitation text.

## Synthetic ground truth

The generator described in [Testing strategy](TESTING_STRATEGY.md) plants
splits, merges, a shared beneficiary, and noise. Ground truth is a file the
test compares against trace output. It is not imported as a finding. A missing
planted path fails the test. An extra path marked `verified` that the truth
file does not contain fails the test. An extra `hypothesis` is allowed only
when the test expects that hypothesis.
