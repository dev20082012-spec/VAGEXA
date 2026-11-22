# Data quality and validation

Every rejected or flagged row is an `ingestion_issues` record with a line
number, field, category, message, and a deterministic suggestion.

| Category | Inserted? |
| --- | --- |
| `empty_file`, `invalid_encoding`, `malformed_csv`, `malformed_json`, `missing_columns` | No. The job is `failed`. |
| `missing_field`, `invalid_amount`, `invalid_currency`, `invalid_timestamp`, `invalid_account`, `unsupported_status`, `malformed_row` | No. The job can still be `succeeded_with_errors` if other rows were inserted. |
| `exact_duplicate` | No. The same canonical content already appeared in this file. |
| `duplicate_source_id` | No. That source id is already stored for the case. |
| `potential_duplicate` | Yes. Same subject, counterparty, amount, currency, and date, with a different source id. The rows are not merged. |

Repeated upload of the same checksum does not parse again.

Logs record the file hash and job status. They do not record narrations or
full account numbers. The API does not return the storage path.
