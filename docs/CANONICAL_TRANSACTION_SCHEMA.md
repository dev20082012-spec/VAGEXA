# Canonical transaction schema

A transaction is one posted leg on one statement. Amount is `numeric(20, 4)`.
The application uses `Decimal`. It does not use binary floating point.

| Field | Meaning |
| --- | --- |
| `id` | Stable internal id |
| `case_id` | Investigation |
| `statement_id` | The subject account's statement for this file |
| `line_number` | Location in the source |
| `source_transaction_id` | Optional id from the dataset. Not globally unique. Unique inside a case when present |
| `direction` | `debit` or `credit` |
| `amount`, `currency` | Positive decimal and ISO code |
| `booking_date`, `booking_time`, `time_precision` | Normalised clock. Missing time stays null |
| `rail` | Payment type after mapping |
| `reference_raw` | Payment reference as supplied |
| `narration_raw` | Original narration |
| `original_record` | The source field map |
| `counterparty_account_id` | Set only when account and IFSC, or a VPA, were supplied |
| `data_classification` | Copied from the case, including `synthetic` |
| `provenance_id` | File hash and parser version |

Transfer rows are stored as debits. The destination account is the
counterparty, not a second invented credit, unless that credit is in the file.
