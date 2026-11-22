# Hackathon demonstration scenario

One investigation. Reference `SYN-DEMO`. Status `open`. Opened `2026-01-20`.
Classification `synthetic`. Generator `demo.v2`. Seed `20261122`. IFSC
`SYNB0000001`. Every account, domain, address, and gateway record is fictional.

The case title is the investigative objective, because that is the text the
workspace shows:

> Determine which records connect a fictional merchant payment to later transfers, and which links remain unresolved.

The checked expectations live in `vagexa.synthetic.demo.ground_truth()`. The
API does not serve that function. The reading copy is
[Ground truth](HACKATHON_GROUND_TRUTH.md). Field-level rows are in
[Demo data dictionary](HACKATHON_DEMO_DATA_DICTIONARY.md).

## Narrative

A fictional inquiry holds bank statements, four DNS answers for a merchant
host and three other hosts, two hosting notes, and three payment-gateway
records. On 15 January 2026 an account pays `100000.0000` INR to another
account. The narration names `syn-a.test`. A separate gateway record names the
same payment reference, the same accounts, and that host. The statements then
show two further transfers of the same amount. A later statement debit leaves
the third account, but the trace horizon stops before that debit is allocated.

On 16 and 17 January a different account receives three credits and pays four
smaller amounts onward. On 19 January a small payment has two gateway records
that name different hosts. Those two records disagree, and both are kept.

Nothing in the file identifies an operator, an account holder, or an offence.

## Timeline

Statement clocks have no time zone and are not converted. DNS, hosting, and
gateway times are UTC.

| When | What is stored |
| --- | --- |
| 2026-01-10 to 2026-01-14 | Ordinary salary, an electricity payment, and a small refund. The refund narration contains `syn-aa.test`, which was not observed. |
| 2026-01-14 10:00 UTC | `syn-a.test` A `203.0.113.50`. |
| 2026-01-15 09:00 | `****0001` pays `****0011` `100000.0000` INR. Reference `UTRSYN0001`. Narration contains `syn-a.test`. |
| 2026-01-15 03:30:20 UTC | Gateway record `SYN-PG-0001` for that reference, settlement account `****0011`, merchant `syn-a.test`. |
| 2026-01-15 09:20 to 11:01 | `****0011` to `****0012` to `****0013`, then a statement debit from `****0013` to `****0019`. |
| 2026-01-16 09:00 to 09:10 | `****0021`, `****0022`, and `****0023` each pay `20000.0000` to `****0030`. |
| 2026-01-16 09:05 UTC | `syn-b.test` A `203.0.113.50`. Same address as the earlier `syn-a.test` answer. No payment names `syn-b.test`. |
| 2026-01-16 11:00 UTC | Two hosting notes, provider `Synthetic Shared Host`, addresses `203.0.113.70` and `203.0.113.71`. |
| 2026-01-16 12:00 UTC | `syn-c.test` AAAA `2001:db8::50`. No payment names it. |
| 2026-01-17 15:00 to 15:15 | `****0030` pays `10000.0000` to each of `****0041` through `****0044`. |
| 2026-01-18 12:00 | `****0051` pays `****0052` `100000.0000` INR. Reference `UNREL`. No gateway record and no host. |
| 2026-01-19 14:00 | `****0070` pays `****0071` `2500.0000` INR. Reference `UTRSYN0090`. The narration names no host. |
| 2026-01-19 14:00:30 and 14:00:40 UTC | Gateway records `SYN-PG-0090` and `SYN-PG-0091` name `syn-d.test` and `syn-e.test` for that same payment. |
| 2026-01-19 08:00 UTC | `syn-d.test` A `203.0.113.80` and `syn-e.test` A `203.0.113.81`. Different addresses. |
| 2026-01-20 10:00 UTC | A later `syn-a.test` A answer, `203.0.113.60`. The earlier answer is kept. |
| 2026-01-20 | The case is opened. |

## What the records support

- `fifo.v1` at horizon 3, seeded on `DEMO-V-1`, allocates three hops and leaves `100000.0000` on `****0013` as `outside_horizon`. `****0019` is on a statement and is not an allocated beneficiary.
- `indicators.v1` for 16–17 January, with the stored defaults, matches `FAN_IN` and `FAN_OUT` on `****0030`. `PASS_THROUGH` does not match: `40000 / 60000` is below `0.85`.
- `correlate.v2` proposes `gateway_merchant` from `****0011` to `syn-a.test` and `mentioned_in` from `****0001` to `syn-a.test`. Both display as `CORROBORATED` because the gateway record and the narration name the same host. Both stay `proposed`.
- The same engine proposes two `gateway_merchant` rows for `UTRSYN0090`. They display as `CONTRADICTED`. Neither record is discarded.
- `syn-a.test` and `syn-b.test` share an address. The two hosting notes share a provider string. Both overlaps display as `UNRESOLVED`. Shared infrastructure is not common ownership.
- No account is linked to `syn-b.test`, `syn-c.test`, or `syn-aa.test`.

## What a judge can say

The supplied statements show three allocated hops and a residual. They also
show three payers into one account and four payments out. One gateway record
and one narration name `syn-a.test`. Another pair of gateway records name two
different hosts for a later payment, and both are still stored. A second
domain was observed at the same address as `syn-a.test`. That is co-occurrence.
It does not identify an operator.
