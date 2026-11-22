# Database design

PostgreSQL 16 is the system of record for identity, casework, money, infrastructure
observations, relationships, jobs, evidence, and audit. Graph algorithms read
from these tables. They do not have a second store in the first release.
See [ADR 0001](decisions/0001-postgresql-system-of-record.md).

Naming: plural tables, `snake_case` columns, UUID primary keys generated with
`gen_random_uuid()`. Timestamps are `timestamptz` and stored in UTC. A statement
date that has no time is a `date`. A clock time supplied without a date is
rejected. Display in `Asia/Kolkata` is a client concern.

Migrations are Alembic revisions. Application code does not create tables on
startup. The first migration enables the `citext` extension for case-insensitive
usernames. `inet`, `gen_random_uuid()`, and `CHECK` constraints come from core
PostgreSQL 16. `pgcrypto` is not required.

## Money and identifiers

- `amount numeric(20, 4)` with `amount > 0`. Direction is separate: `debit` or `credit`.
- More than four decimal places is a parser error, not a rounding event.
- `currency char(3)` is required. There is no database default. A forgotten currency must fail.
- JSON and the API represent amounts as strings.
- Account numbers are stored raw and normalised (whitespace removed). IFSC is stored uppercased. A UPI VPA is stored lowercased.
- Uniqueness of a bank account is `(account_number_norm, ifsc_norm)` where both are present. Uniqueness of a VPA is `vpa_norm` where present. A holder name is never a unique key.
- Do not add a float column, a double precision column, or a `is_mule` column.

## Data classification

Every fact table below includes a classification, except the instrument keys
`accounts`, `domain_names`, and `ip_addresses`:

```text
data_classification text not null
  check (data_classification in
    ('official','public_intelligence','synthetic','derived','unverified'))
```

Cases add:

```text
check (
  (data_classification = 'synthetic' and synthetic_batch_id is not null)
  or
  (data_classification <> 'synthetic' and synthetic_batch_id is null)
)
```

Child rows must match the case classification for `official` and `synthetic`.
Instrument keys (`accounts`, `domain_names`, `ip_addresses`) do not carry a
holder name or a classification. They are unique inside one database, and one
database is one data mode. Printed names and source classifications live on
append-only observations. See ADR 0013.
`derived` rows (traces, indicators, findings) cite the inputs that produced
them. `public_intelligence` and `unverified` may appear as observations attached
to a case and must still carry provenance. They do not reclassify the case.

The application reads `VAGEXA_DATA_MODE`:

| Mode | Insert allowed for primary case records | Insert refused |
| --- | --- | --- |
| `synthetic` | `synthetic` | `official` |
| `operational` | `official` | `synthetic` |

`derived`, `public_intelligence`, and `unverified` are allowed in both modes
when their provenance says what they are. A case row itself is only `official`
or `synthetic` in the first release, so a case cannot be a mixture.

## Identity and access

### `users`

`id`, `username` (citext, unique), `password_hash`, `display_name`, `status`
(`active` or `disabled`), `created_at`.

Email may be added when there is a real need. It is not required for the first
local-account slice.

### `roles`

`id`, `name` unique: `administrator`, `investigator`, `analyst`, `auditor`.

### `user_roles`

`user_id`, `role_id`, primary key of both.

### `sessions`

`id`, `user_id`, `token_hash` unique, `created_at`, `expires_at`, `revoked_at`,
`user_agent`, `client_ip`.

The raw session token exists only in the cookie. The client IP is personal data
used for session review. It is not copied into analytical logs.

### `case_assignments`

`case_id`, `user_id`, `case_role` (`lead`, `investigator`, `analyst`,
`auditor`), `assigned_at`, `assigned_by`. Primary key `(case_id, user_id)`.

## Casework

### `cases`

`id`, `reference` unique, `title`, `status` (`open`, `closed`),
`data_classification`, `synthetic_batch_id` null, `opened_on` date,
`created_by`, `created_at`.

### `complaints`

`id`, `case_id`, `external_reference`, `reported_at` null, `narrative`,
`data_classification`, `provenance_id`, `created_at`.

Narrative is case data. Queries for the copilot may read it under authorisation.
Logging it is forbidden.

### `parties`

`id`, `display_name`, `party_kind` (`person`, `organisation`, `unknown`),
`data_classification`, `created_at`.

Parties are created by an investigator action or by a deterministic account
grouping. They are not created because two names look similar.

### `accounts`

Immutable instrument key. `id`, `kind` (`bank` or `vpa`; `wallet` is reserved
and must not be inserted until a key scheme exists), `account_number_norm`,
`ifsc_norm`, `vpa_norm`, `created_at`.

No holder name, no bank name, and no classification on this row. Those columns
are not added back as a convenience. Partial unique indexes:

- `(account_number_norm, ifsc_norm)` where both are not null;
- `(vpa_norm)` where not null.

Updates and deletes are rejected by trigger.

### `account_observations`

Append-only. `id`, `account_id`, `case_id`, `statement_id` null,
`account_number_raw` null, `holder_name_raw` null, `bank_name_raw` null,
`data_classification`, `provenance_id`, `created_at`.

Two files may record two holder names for one instrument. Both rows stay. The
application does not choose a current name.

### `account_party_links`

`id`, `account_id`, `party_id`, `link_kind` (`named_holder`,
`investigator_attributed`), `assertion_kind`, `provenance_id`, `created_by`,
`created_at`.

A named holder copied from a statement is `verified` against that statement.
An investigator attribution is recorded as their action and is not upgraded to
a bank-verified identity.

## Statements and transactions

### `source_files`

`id`, `case_id`, `sha256`, `byte_size`, `original_filename`, `media_type`,
`storage_key` (server-generated; the original filename is never a path
segment), `status` (`stored`, `parsed`, `rejected`), `data_classification`,
`uploaded_by`, `uploaded_at`, `provenance_id`.

Unique `(case_id, sha256)`.

### `statements`

`id`, `case_id`, `source_file_id`, `account_id`, `parser_name`,
`parser_version`, `period_start` date null, `period_end` date null,
`currency`, `institution_name` null, `data_classification`, `provenance_id`,
`supersedes_statement_id` null.

`account_id` is the subject account, the account whose ledger this file is.
A successful parse does not leave it null. It is supplied with the upload as
an account number and IFSC, or as a VPA. It is not guessed from a balance
pattern. A missing subject rejects the job and keeps the bytes.

`supersedes_statement_id` points at the previous parse of the same file.
Analytical queries use transactions whose statement has no newer row pointing
at it. ADR 0012.

### `transactions`

`id`, `statement_id`, `case_id`, `line_number`, `booking_date`, `booking_time`
null, `value_date` null, `time_precision` (`date` or `time`), `direction`,
`amount`, `currency`, `balance_after` null, `rail` (`upi`, `imps`, `neft`,
`rtgs`, `cash`, `cheque`, `card`, `internal`, `unknown`), `counterparty_raw`
null, `reference_raw` null, `narration_raw`, `extracted_vpa` null,
`extracted_utr` null, `extractor_version` null, `counterparty_account_id` null,
`counterparty_resolution` (`structured_field`, `narration_pattern`,
`unresolved`), `data_classification`, `provenance_id`.

Unique `(statement_id, line_number)`.

Index `(case_id, booking_date)` and `(counterparty_account_id)`.

A structured counterparty field may set `counterparty_account_id` with
resolution `structured_field`. A narration pattern may set it only when the
extractor returns a single unambiguous VPA or account-plus-IFSC, and the
resolution value is `narration_pattern`. The relationship assertion kind for
the former is `verified`. For the latter it is `inferred`.

## Traces and indicators

### `analytical_runs`

`id`, `case_id`, `run_kind` (`trace`, `indicators`, `correlation`, `copilot`),
`method_name`, `method_version`, `parameters jsonb`, `input_hash`,
`output_hash` null, `status` (`running`, `succeeded`, `failed`), `error_code`
null, `requested_by`, `created_at`.

Migration `20261122_0004` creates the analytical tables used by `fifo.v1` and
`indicators.v1`. The live check constraint on `run_kind` is `trace`,
`indicators`, and `statement_walk`. Status values inserted by the application
are `succeeded` and `failed`, because the run finishes before the row is
written. `output jsonb` holds an observed statement sequence. `complaint_id`
is present and nullable, with no foreign key, until a complaints table exists.

Parameters are the policy knobs, not a copy of narrations.

### `trace_seeds`

`analytical_run_id`, `transaction_id`, `complaint_id` null. Primary key
`(analytical_run_id, transaction_id)`.

### `trace_flows`

`id`, `analytical_run_id`, `case_id`, `origin_complaint_id` null,
`from_account_id`, `to_account_id` null, `exit_kind` null, `source_transaction_id`,
`amount`, `currency`, `layer_to` integer check (`layer_to` between 0 and 5),
`assertion_kind`, `method_name`, `method_version`.

`from_account_id` is always set. `to_account_id` is null only when `exit_kind`
is `cash` or `unresolved`. A cash withdrawal is an exit from the subject
account, not a null source. The row must not contain a synthesised destination
account. Layer 0 is the seeded source side and is not required to be its own
flow row; the first emitted flow may be layer 1.

### `trace_residuals`

`id`, `analytical_run_id`, `account_id`, `complaint_id` null, `amount`,
`currency`, `reason` (`no_onward_record`, `outside_horizon`, `unallocated`).

### `account_indicators`

`id`, `analytical_run_id`, `case_id`, `account_id`, `code`, `window_start`,
`window_end`, `threshold jsonb`, `support_transaction_ids uuid[]`,
`assertion_kind`, `method_name`, `method_version`, `limitations`.

`assertion_kind` for a rule match is `inferred`. `limitations` is `not null`.

There is no table of guilt labels.

## Infrastructure observations

### `domain_names`

`id`, `name_norm` unique (lowercased, trailing dot removed), `created_at`.

### `ip_addresses`

`id`, `address` unique, `created_at`. Store as `inet`.

### `autonomous_systems`

`id`, `asn` unique, `name` null, `created_at`.

### `dns_observations`

`id`, `domain_id`, `rrtype`, `rdata`, `observed_at`, `resolver`,
`provenance_id`, `data_classification`.

Observations are immutable. A later lookup inserts a new row. "Current"
resolution is the latest observation, and the API says so.

Migration `20261122_0005` adds `case_id` on `dns_observations`. A global read
would expose another case's collection time. Phase 1 stores `A` and `AAAA`
only. `ip_address_id` points at the normalised answer. Certificate and ASN
tables are still not created.

### `hosting_observations`

`id`, `case_id` null, `ip_address_id` null, `autonomous_system_id` null,
`provider_name` null, `source_note`, `observed_at`, `provenance_id`,
`data_classification`.

A manual investigator note and a later ASN adapter both use this table. The
provenance method distinguishes them. An investigator note requires `case_id`.
A null `case_id` is allowed only for a public mapping that contains no case
narrative. Reading a case-scoped note uses that case's assignment.

## Relationships

### `relationships`

`id`, `case_id`, `from_kind`, `from_id`, `to_kind`, `to_id`, `rel_type`,
`assertion_kind`, `method_name`, `method_version`, `status` (`proposed`,
`confirmed`, `rejected`), `provenance_id`, `created_by`, `created_at`,
`decided_by` null, `decided_at` null.

`case_id` is required. Cross-case co-occurrence is a query, not a row with a
null case. `from_kind` and `to_kind` are a closed set: `account`, `party`,
`complaint`, `domain`, `ip`, `autonomous_system`. Polymorphic ends have no
database foreign key; the write path must reject an unknown id.

Confirmed and rejected rows stay. A new decision inserts an audit event and
updates only `status`, `decided_by`, and `decided_at` on this workflow table.
That is a deliberate exception to append-only evidence: the relationship row is
workflow state, and the evidence of the decision is the audit event plus the
provenance of the underlying facts. The status columns are the only ones an
update may touch. A trigger enforces that.

Migrations `20261122_0006` and `20261122_0007` implement this table with
`analytical_run_id`, a `pair_key` unique per case, `limitation`, and
`explanation`. The live `rel_type` set is `mentioned_in`,
`infrastructure_overlap`, `same_payment`, and `gateway_merchant`. Support rows
are in `relationship_support` (`transaction`, `dns_observation`,
`hosting_observation`, `gateway_record`). Each decision also inserts a
`relationship_reviews` row with the reason. Both are append-only.

### `gateway_records`

Migration `20261122_0007`. Append-only. One row per payment-gateway record:
`id`, `case_id`, `source_record_id` (unique per case), `source_system`,
`payment_reference`, `payer_account_id` null, `payee_account_id`,
`merchant_domain_id`, `merchant_label`, `amount numeric(20,4)`, `currency`,
`processed_at timestamptz`, `original_record jsonb`, `data_classification`,
`provenance_id`, `created_at`.

This is a third-party source record, not an analytical result. In this
release only the synthetic demonstration writes it, with source system
`synthetic_payment_gateway`. It names a settlement account for a merchant
domain. It does not identify who operates the domain.

### `resolution_decisions`

`id`, `left_kind`, `left_id`, `right_kind`, `right_id`, `decision` (`merge`,
`reject`), `reason`, `decided_by`, `created_at`.

A merge also inserts a `same_as` relationship. Neither side is deleted.

## Evidence and audit

### `provenance_records`

`id`, `data_classification`, `source_system`, `source_reference`,
`collected_at`, `collected_by`, `method_name`, `raw_hash` null.

`source_reference` is a file hash plus line, a URL of a public lookup, or a
synthetic batch id. It is not a blob.

### `evidence_records`

`id`, `case_id`, `provenance_id`, `kind` (`source_file`, `transaction`,
`observation`, `analytical_finding`, `report`), `object_id`, `content_hash`,
`supersedes_id` null, `created_at`.

No `updated_at`. Update and delete triggers raise an exception.

### `findings`

`id`, `analytical_run_id`, `case_id`, `finding_kind`, `summary`,
`assertion_kind`, `limitations`, `method_name`, `method_version`.

`limitations` is `not null` and must be non-empty at the application boundary.

### `finding_support`

`finding_id`, `evidence_id`, primary key of both.

### `audit_events`

`id` bigserial, `occurred_at`, `actor_id` null, `action`, `case_id` null,
`object_kind`, `object_id`, `request_id`, `outcome` (`success`, `denied`,
`failure`), `detail jsonb`.

`detail` may contain redacted suffixes and method names. It must not contain
narration, full account numbers, VPAs, or questions. Update and delete triggers
raise an exception.

Actions required in the first slice: `auth.login`, `auth.logout`, `case.open`,
`statement.upload`, `trace.run`, `relationship.decide`, `copilot.query`,
`report.export`, `cross_case.lookup`.

### `copilot_queries`

`id`, `case_id`, `actor_id`, `mode` (`deterministic`, `assisted`),
`question_text`, `tool_trace jsonb`, `evidence_bundle_hash`, `response jsonb`,
`model_id` null, `created_at`.

This table is case data. It is readable only through the case authorisation
path. It is append-only.

## Jobs and synthetic batches

### `jobs`

`id`, `kind`, `case_id`, `payload jsonb`, `status` (`queued`, `running`,
`succeeded`, `failed`), `attempts`, `locked_at`, `locked_by`, `error_code`
null, `created_at`, `finished_at` null.

`payload` holds UUIDs such as `source_file_id`. Index `(status, created_at)`.

### `synthetic_batches`

`id`, `scenario_key`, `generator_version`, `ground_truth_sha256`, `created_at`.

The ground-truth document is a test fixture hashed here so a batch can be
identified. The document is not loaded into investigator tables and is not
granted to the application role as a readable answer key.

## Database roles

Designed now, enforced in deployment before operational data:

| Role | Rights |
| --- | --- |
| `vagexa_migrator` | Schema migrations. |
| `vagexa_app` | DML on workflow tables. `INSERT` only on provenance, evidence, findings, analytical runs, copilot queries, and audit. `UPDATE` of `relationships` limited to status columns. |
| `vagexa_auditor` | `SELECT` on audit, evidence, and case tables. |

The first local demo may use one login, and the append-only triggers still run.
The single login is a known gap recorded in the roadmap, not an acceptable end
state for official records.

## Integrity triggers

- `BEFORE UPDATE OR DELETE` on `provenance_records`, `evidence_records`,
  `findings`, `finding_support`, `analytical_runs`, `trace_flows`,
  `trace_residuals`, `account_indicators`, `transactions`, `dns_observations`,
  `account_observations`, `accounts`, `copilot_queries`, and `audit_events`
  raises an exception.
- `BEFORE UPDATE` on `relationships` raises an exception unless the only changed
  columns are `status`, `decided_by`, and `decided_at`.
- Transactions are not edited. A parser correction inserts a superseding
  evidence record and a new statement version. The original rows remain.

These triggers are part of the first migration, not a later hardening pass.
They are the mechanism that keeps a convenience `UPDATE` from rewriting history.

## Indexes and growth

First indexes are the foreign keys, the case-and-date transaction index, the
account uniqueness indexes, and the job status index. Transaction partitioning
by month is a later physical change. It is not required to start, and it must
not change the logical model.

Full-text search on narrations is deferred. If it is added, the index is not a
licence to log the text it indexes.
