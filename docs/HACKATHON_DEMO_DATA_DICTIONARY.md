# Hackathon demo data dictionary

Case `SYN-DEMO`, classification `synthetic`, generator `demo.v2`, seed
`20261122`. IFSC `SYNB0000001`. Source ids are stable. A second
`python -m vagexa.demo_seed` inserts no second copy of a statement, DNS row,
hosting note, gateway record, or relationship.

The machine-checked expectations are `vagexa.synthetic.demo.ground_truth()`.
That function is not served by the API. Role words such as "victim" are not
stored on the case.

Amounts are decimal strings with four places. Currency is `INR` on every row
in this case. Statement clocks have no time zone. Other observation times are
UTC.

## Counts

| Record | Count |
| --- | --- |
| Statements | 14 |
| Transaction rows | 25 |
| Statement debits | `604819.5000` |
| Statement credits | `607500.0000` |
| DNS observations | 6 |
| Hosting notes | 2 |
| Gateway records | 3 |
| Relationships | 15 |
| Findings | 18 |

The debit and credit totals differ because several transfers have only one
statement. The missing side is not invented.

## Accounts

| Masked | Role in the story | Own statement rows |
| --- | --- | --- |
| `****0001` | Pays `100000.0000` on 2026-01-15 09:00. Reference `UTRSYN0001`. Narration names `syn-a.test`. Source `DEMO-V-1`. | 1 debit |
| `****0011`, `****0012`, `****0013` | Next accounts on 15 January. References `UTRSYN0002`, `UTRSYN0003`, `UTRSYN0004`. | 2 each |
| `****0019` | Statement credit from `****0013`. Not allocated at horizon 3. | 1 credit |
| `****0021`, `****0022`, `****0023` | Each pays `20000.0000` to `****0030` on 16 January. References `FAN1`, `FAN2`, `FAN3`. | 1 debit each |
| `****0030` | Receives those three credits and pays four `10000.0000` transfers on 17 January. References `OUT1` to `OUT4`. | 3 credits, 4 debits |
| `****0041` to `****0044` | Destinations of those four payments. No statements of their own. | 0 |
| `****0051`, `****0052` | Unrelated `100000.0000` transfer on 18 January. Reference `UNREL`. | 1 each |
| `****0060` | Ordinary account. Salary `45000.0000`, electricity `1820.5000`, refund `499.0000`. | 1 credit, 2 debits |
| `****0061` to `****0063` | Counterparties of the ordinary rows. No statements of their own. | 0 |
| `****0070`, `****0071` | `2500.0000` on 19 January. Reference `UTRSYN0090`. Sources `DEMO-D-OUT` and `DEMO-D-IN`. Narration names no host. | 1 each |

## Infrastructure

Resolver label on every DNS row: `synthetic_fixture`. No live lookup was made.
Addresses are documentation ranges.

| Record | Value | Why it is here |
| --- | --- | --- |
| DNS | `syn-a.test` A `203.0.113.50` at 2026-01-14T10:00:00Z | Host named in `DEMO-V-1` and in `SYN-PG-0001`. |
| DNS | `syn-b.test` A `203.0.113.50` at 2026-01-16T09:05:00Z | Same address. No payment names this host. |
| DNS | `syn-a.test` A `203.0.113.60` at 2026-01-20T10:00:00Z | Later answer. The earlier answer stays. |
| DNS | `syn-c.test` AAAA `2001:db8::50` at 2026-01-16T12:00:00Z | Unrelated host. |
| DNS | `syn-d.test` A `203.0.113.80` at 2026-01-19T08:00:00Z | Host named only by `SYN-PG-0090`. |
| DNS | `syn-e.test` A `203.0.113.81` at 2026-01-19T08:00:00Z | Host named only by `SYN-PG-0091`. Different address from `syn-d.test`. |
| Hosting | `203.0.113.70` and `203.0.113.71`, provider `Synthetic Shared Host` | Same provider string, different addresses. |
| Narration only | `syn-aa.test` on `DEMO-N-3` | Near-name. Not observed, so no link is proposed. |

No certificate, nameserver, registrar, ASN, or geolocation row is stored.

## Gateway records

All three use source system `synthetic_payment_gateway` and currency `INR`.

| Source id | Reference | Payer | Payee | Merchant | Amount | Processed (UTC) |
| --- | --- | --- | --- | --- | --- | --- |
| `SYN-PG-0001` | `UTRSYN0001` | `****0001` | `****0011` | `syn-a.test`, Synthetic Merchant A | `100000.0000` | 2026-01-15T03:30:20Z |
| `SYN-PG-0090` | `UTRSYN0090` | `****0070` | `****0071` | `syn-d.test`, Synthetic Service D | `2500.0000` | 2026-01-19T14:00:30Z |
| `SYN-PG-0091` | `UTRSYN0090` | `****0070` | `****0071` | `syn-e.test`, Synthetic Service E | `2500.0000` | 2026-01-19T14:00:40Z |

`SYN-PG-0090` and `SYN-PG-0091` are the same payment described twice, with
different merchant hosts. The correlation rule reads these stored rows. It
does not link a payment to a host merely because both sit on this case.
