# Evidence data contract

Every analytical claim points at the records it used. This contract is the
shape of that pointer. It does not make a result admissible in court, and it
does not certify the software as a forensic tool. Hashes and triggers detect
ordinary application rewrites. A database superuser can still change storage.
That limit is stated on the report.

## Classes

| Class | Example | Mutable |
| --- | --- | --- |
| Source | Uploaded CSV bytes | The blob is not overwritten. A new upload with a new hash is a new file. |
| Normalised | Transaction row, account observation, DNS observation | Insert only |
| Derived | Flow, residual, indicator, finding | Insert only, tied to one run |
| Analyst-created | Complaint, annotation, relationship decision | Notes and complaints are insert-only. Relationship status is the only in-place decision, and it is audited. |

## Provenance record

Required on every source and normalised row:

| Field | Content |
| --- | --- |
| `data_classification` | `synthetic` for this release's fixture |
| `source_system` | `upload`, `investigator_entry`, `synthetic_generator`, or `method` |
| `source_reference` | File hash plus line, or observation id, or scenario key |
| `collected_at` | When the file was uploaded or the note was entered. Not an invented bank time. |
| `collected_by` | User id or `synthetic_generator` |
| `method_name` | `csv_canonical.v1`, `narration_extractor.v1`, `investigator_entry` |
| `raw_hash` | SHA-256 of the bytes when bytes exist |

Original printed values stay on the normalised row: `narration_raw`,
`counterparty_raw`, `account_number_raw`, `holder_name_raw`. Normalised keys
live on `accounts` and are not a replacement for the printed strings.

## Derived claim

An `analytical_runs` row stores `method_name`, `method_version`, `parameters`,
`input_hash`, and, on success, `output_hash`.

`input_hash` is SHA-256 of canonical JSON: sorted keys, UTF-8, amounts as
strings, of the seed ids, the current statement ids, and the parameters.

`output_hash` covers the published flows or indicator rows in the same
canonical form.

A finding stores `summary`, `assertion_kind`, `limitations` (non-empty),
method name, and method version. `finding_support` lists `evidence_records`
ids. A finding with an empty support list for a positive claim is not inserted.
A residual is a positive claim of a gap and cites the run and the account.

## Contradiction and support

Two holder names are two observations. Both evidence rows remain. The UI lists
both. Nothing marks one as the winner.

Two proposed relationships that disagree both remain until a person rejects
one. Rejection keeps the row and sets `status=rejected`.

Corroboration is additional evidence ids on the same finding. It does not
change `assertion_kind` and it is not a percentage.

## Analyst decisions

| Act | Stored as |
| --- | --- |
| Confirm or reject | `relationships.status`, `decided_by`, `decided_at`, plus `relationship.decide` |
| Note | `annotations` row and an evidence row of kind `annotation`. The report may quote it only under the heading "Analyst notes". |
| Seed choice | `trace_seeds` |

A note cannot move a hypothesis to `verified`.

## Processing times

`collected_at` is when the source entered the system.
`analytical_runs.created_at` is when the method ran.
Transaction `booking_date` is the bank's date, copied, not replaced by either
of those clocks.

## Integrity

- SHA-256 of source bytes on `source_files.sha256` and in provenance.
- Append-only triggers on transactions, observations, flows, findings, evidence, provenance, annotations, copilot queries, and audit.
- Relationship updates cannot touch amount, kind, or endpoints.
- Reprocess inserts a statement with `supersedes_statement_id`. Queries that feed methods use the latest statement in that chain. Older transactions remain and keep their hashes.
- Reports store their own SHA-256 as an evidence row of kind `report`.

## What the export contains

The HTML report lists, in order: classification banner, exporter and time,
source-file hashes and parser versions, seeds, policy and parameters, flows
with assertion kinds, residuals, indicators with support ids, observations
with times, relationships split into confirmed, proposed, and rejected,
analyst notes in their own section, limitations, and the sentence that
indicators and attributed paths are not determinations of guilt.

The export fails if the limitations section would be empty.

## Synthetic data

Fixture rows are `synthetic`. The ground-truth file is hashed onto
`synthetic_batches` and is not returned by any route. Tests read it from
`backend/tests/fixtures/`. Mixing `official` into this database mode is a
rejected insert.
