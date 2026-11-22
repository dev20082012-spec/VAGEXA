# 0012. Statement subject is required, and reprocessing appends

- Status: accepted
- Date: 2026-11-22

## Context

The canonical CSV described counterparties and not the account whose statement
was uploaded. The statement's `account_id` was nullable and the design forbade
guessing it from the balance. Direction, layers, and FIFO have no meaning
without that subject.

Separately, upload idempotency on file hash returned the existing parse
forever. Evidence supersession lived on `evidence_records`, while traces read
`transactions`. A parser bug could not be corrected without either freezing
the bad rows in every query or inserting a second live copy.

## Decision

A statement job is rejected, with the bytes retained, unless the upload
supplies a subject account number and IFSC, or a subject VPA. The accepted
statement's `account_id` is not null.

The file hash remains unique per case. A second upload of the same bytes does
not create a second blob and does not, by itself, parse again.

Reprocess is an explicit job. It inserts a new `statements` row with
`supersedes_statement_id` set to the previous statement, a new parser version,
and new transaction rows. Analytical queries, traces, and indicators include
transactions whose statement is not superseded by a later row. The old rows
stay stored.

## Consequences

- Victim-only files still cannot show later hops. They can show the hops named
  on that statement.
- Idempotent upload and correctable parsing are different operations.
- Reports list the parser version that produced the rows they include.

## Alternatives

- Guess the subject from the most frequent counterparty. That fabricates the
  owner of the ledger. Rejected.
- Update transactions in place on reprocess. That destroys the first parse.
  Rejected.
- Forbid reprocess. The first parser bug becomes the permanent case. Rejected.
