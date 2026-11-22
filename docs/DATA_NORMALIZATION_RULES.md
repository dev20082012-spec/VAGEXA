# Data normalisation rules

Parser version `ingest.v1`.

- Account numbers lose internal spaces. IFSC is uppercased and must match
  `^[A-Z]{4}0[A-Z0-9]{6}$` when present. VPAs are lowercased.
- Currency is three letters, uppercased. No exchange rate is applied.
- Amounts are `Decimal`. More than four decimal places, zero, negatives, and
  scientific notation are rejected.
- Dates `YYYY-MM-DD` and `DD/MM/YYYY` stay dates. `YYYY-MM-DDTHH:MM:SS`, a
  space instead of `T`, a trailing `Z`, or an offset keep the clock time in
  the source text. The offset is not used to move the calendar date. The
  original string remains in `original_record`.
- Transfer `status` must be `posted` or `completed`. Other statuses are
  issues, not transactions.
- `transaction_type` maps to a known rail, otherwise `unknown`.
- Unexpected columns are listed on the job and are not stored as transactions.
- The original file bytes are not rewritten.
