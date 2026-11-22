# Account behaviour analysis

`GET /api/v1/cases/{case_id}/activity` summarises current statement rows.
`GET /api/v1/cases/{case_id}/financial-summary` adds the transaction count,
the currencies present, the latest trace status, and the latest indicator
codes. Those figures are counts of stored rows.

## Metrics

For each statement subject and currency:

- incoming count and amount (credits)
- outgoing count and amount (debits)
- unique structured counterparties
- average, median, and maximum amount
- first and last booking date
- row count and how many rows are date-only

Amounts are `Decimal`, quantised to four places, half up for the average and
the even-count median. The other side of a transfer is not added again, so a
debit and its mirror credit are not summed into one account.

## Limits

- Currencies are not added together and are not converted. There is no rate
  table.
- No separate baseline period is stored, so a change from a historical
  baseline is not computed. The coverage sentence says that, including that a
  dormant-to-active comparison is not made.
- An account that appears only as a counterparty is omitted until its own
  statement is loaded. Its absence is not stored as zero activity.
- The summary does not infer who owns the account.

Transaction search is `GET /api/v1/cases/{case_id}/transactions` with
direction, rail, currency, booking dates, amount bounds, statement account,
and exact source transaction id. Pages are limited to 100 rows and the offset
cannot pass 10,000. Sort is booking date, time with nulls last, then line
number. Narration text is not a search field.
