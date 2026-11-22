# Financial data ingestion

Phase 1 ingestion turns a CSV or JSON dataset into canonical statement legs.
The original bytes are stored under a server-generated key. The filename is
metadata only. Parsing, validation, and inserts finish before the upload
response returns, and the job row records the outcome. A later worker can
claim the same `jobs` table. This release does not run a separate worker
process.

## Formats

Content is detected from the bytes, not from the extension.

- Statement CSV or JSON uses `line_number`, `booking_date`, `direction`,
  `amount`, `currency`, and `rail`. The subject account is supplied with the
  upload.
- Transfer CSV or JSON uses `source_account`, `destination_account`, `amount`,
  and `currency`. Each posted row becomes a debit on the source account, with
  the destination as the structured counterparty. A destination statement is
  not invented.

JSON is an array of objects, or `{ "records": [ ... ] }`.

## Job status

`queued` and `cancelled` exist for a later worker. This release finishes the
job inside the request:

- `failed` means the file could not be read: empty, bad encoding, malformed
  syntax, or missing columns. No transactions are inserted. The issue explains
  why.
- `succeeded` means every data row was inserted and no issues were recorded.
- `succeeded_with_errors` means processing finished and at least one row was
  rejected or flagged. Rejected rows are in `ingestion_issues`. They are not
  dropped quietly.

Uploading the same bytes again for the same case returns the original job with
`idempotent_replay` and does not insert more transactions.

## What this is not

This is not fund tracing. It does not score mule behaviour. Synthetic cases
remain labelled synthetic.
