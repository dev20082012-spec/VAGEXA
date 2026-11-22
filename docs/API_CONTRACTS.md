# API contracts

Version prefix `/api/v1`. Cookie session. Amounts are strings. Dates are
`YYYY-MM-DD`. Instants are ISO-8601 with a numeric offset. Unknown case and
unauthorised case are both 404.

Errors are `application/problem+json`:

```json
{
  "type": "https://vagexa.local/problems/invalid",
  "title": "Invalid request",
  "status": 422,
  "detail": "Subject account is required.",
  "instance": "/api/v1/cases/3f1c/statements",
  "request_id": "req_01",
  "errors": [{ "field": "subject_account", "reason": "required" }]
}
```

`detail` does not include SQL, file paths, or another case's title.
Lists are `{ "items": [], "next_cursor": null }` with `limit` default 50 and
maximum 200.

| Status | When |
| --- | --- |
| 401 | No session |
| 403 | Role cannot do the action, and the case itself is visible |
| 404 | Missing or not assigned |
| 409 | Duplicate decision, report without a trace, DNS lookup while intel is off |
| 413 | Upload over 25 MB |
| 422 | Schema, classification, hop cap, unknown tool |
| 500 | Generic internal |

## Authentication

### `POST /api/v1/auth/login`

No session. Body `{ "username": "demo", "password": "set-at-runtime" }`.
Response 200 sets `Set-Cookie` and returns:

```json
{
  "user": { "id": "uuid", "username": "demo", "display_name": "Demo Investigator" },
  "roles": ["investigator"],
  "data_mode": "synthetic"
}
```

Audit `auth.login` or `auth.login_failed`. The failed detail has no password.
401 uses the same title for unknown user and bad password.

### `POST /api/v1/auth/logout`

Session required. Revokes the row. Audit `auth.logout`. 204.

### `GET /api/v1/auth/me`

Session required. Same body as login without setting a cookie.

## Users

Administrator global role. These routes do not accept a case id and do not
return case content.

### `POST /api/v1/users`

```json
{ "username": "analyst1", "display_name": "Analyst One", "password": "set-at-runtime", "roles": ["analyst"] }
```

201 returns the user without `password` or `password_hash`. 409 duplicate
username. 403 otherwise. Audit `user.create`.

### `GET /api/v1/users`

Administrator. Cursor list of id, username, display name, status, roles.

### `POST /api/v1/users/{user_id}/disable`

Administrator. 204. Audit. Does not delete sessions' audit history. Revokes
live sessions.

## Cases

### `POST /api/v1/cases`

Caller has global role `investigator` or `administrator`.

```json
{
  "reference": "SYN-A",
  "title": "Synthetic chain",
  "opened_on": "2026-01-15",
  "data_classification": "synthetic",
  "synthetic_batch_id": "uuid"
}
```

201. The creator is assigned `lead` in the same transaction. `official` in
synthetic mode is 422. Audit `case.create`.

### `GET /api/v1/cases`

Assigned cases only. Items: id, reference, title, status, data_classification.

### `GET /api/v1/cases/{case_id}`

Assigned. Header plus counts of statements, transactions, open proposals.

```json
{
  "id": "uuid",
  "reference": "SYN-A",
  "title": "Synthetic chain",
  "status": "open",
  "data_classification": "synthetic",
  "opened_on": "2026-01-15",
  "counts": { "statements": 4, "transactions": 8, "proposed_relationships": 1 }
}
```

Audit `case.open` the first time in a session. 404 for an unassigned
administrator.

### `POST /api/v1/cases/{case_id}/assignments`

Global administrator.

```json
{ "user_id": "uuid", "case_role": "analyst" }
```

201. Audit `assignment.create`. 404 if the administrator is not... no: this
route is global administrator power and does not require the administrator to
be assigned. It returns the assignment, not the case narrative.

### `POST /api/v1/cases/{case_id}/complaints`

Assigned `lead` or `investigator`.

```json
{
  "external_reference": "CMP-1",
  "reported_at": "2026-01-15T10:00:00+05:30",
  "narrative": "Synthetic complaint text."
}
```

201. Audit. Narrative is not logged.

### `GET /api/v1/cases/{case_id}/complaints`

Assigned. Cursor list.

## Statements and transactions

### `POST /api/v1/cases/{case_id}/statements`

Assigned investigator. `multipart/form-data` fields: `file`,
`subject_account`, `subject_ifsc`, or `subject_vpa` instead of the pair,
`currency`.

202:

```json
{ "job": { "id": "uuid", "status": "queued", "kind": "parse_statement" } }
```

Same hash: 200 and the existing file, no new job. Missing subject: 422.
Over 25 MB: 413. Audit `statement.upload`.

### `POST /api/v1/statements/{statement_id}/reprocess`

Assigned investigator. 202 job kind `reprocess_statement`. Audit
`statement.reprocess`.

### `GET /api/v1/jobs/{job_id}`

Assigned to the job's case.

```json
{
  "id": "uuid",
  "kind": "trace",
  "status": "succeeded",
  "error_code": null,
  "analytical_run_id": "uuid"
}
```

### `GET /api/v1/cases/{case_id}/transactions`

Assigned. Filters: `direction`, `rail`, `booking_date_from`, `booking_date_to`.
Current statements only unless `include_superseded=true`, which an auditor
may set and an investigator may set. Default is current.

Item:

```json
{
  "id": "uuid",
  "line_number": 1,
  "booking_date": "2026-01-15",
  "booking_time": "09:00:00",
  "time_precision": "time",
  "direction": "debit",
  "amount": "100000.0000",
  "currency": "INR",
  "rail": "imps",
  "counterparty_masked": "****0011",
  "counterparty_resolution": "structured_field",
  "source_file_sha256": "ab",
  "evidence_id": "uuid"
}
```

### `GET /api/v1/cases/{case_id}/accounts`

Assigned. Instruments cited by the case, with the observations for this case
only. Masked keys in the list.

### `GET /api/v1/accounts/{account_id}`

404 unless the caller is assigned to at least one case that cites it.
Response includes full number, IFSC or VPA, and the observations from cases
the caller is assigned to. It does not include other cases' narratives.

## Traces and indicators

### `POST /api/v1/cases/{case_id}/traces`

Assigned investigator or analyst.

```json
{
  "seed_transaction_ids": ["uuid"],
  "policy": "fifo",
  "policy_version": "fifo.v1",
  "max_layer": 3
}
```

202 with job id and `analytical_run_id`. `max_layer` above 5 is 422.
Audit `trace.run`.

### `GET /api/v1/traces/{trace_id}`

Assigned to the run's case.

```json
{
  "id": "uuid",
  "status": "succeeded",
  "method_version": "fifo.v1",
  "max_layer": 3,
  "flows": [
    {
      "from_account_masked": "****0001",
      "to_account_masked": "****0011",
      "amount": "100000.0000",
      "currency": "INR",
      "layer_to": 1,
      "assertion_kind": "verified",
      "evidence_ids": ["uuid"]
    }
  ],
  "residuals": [
    {
      "account_masked": "****0013",
      "amount": "100000.0000",
      "currency": "INR",
      "reason": "outside_horizon"
    }
  ],
  "limitations": "Horizon 3. Amounts are inside the supplied statements. outside_horizon is not an attributed beneficiary."
}
```

### `POST /api/v1/cases/{case_id}/indicator-runs`

Assigned investigator or analyst. Body is the `indicators.v1` input from the
algorithm spec. 202.

### `GET /api/v1/cases/{case_id}/indicators`

Assigned. Latest succeeded rows. No guilt field.

```json
{
  "items": [
    {
      "code": "FAN_IN",
      "assertion_kind": "inferred",
      "method_version": "indicators.v1",
      "support_transaction_ids": ["uuid"],
      "limitations": "Verified edges only. Narration-derived links were excluded. This is a rule match."
    }
  ]
}
```

## Graph

### `GET /api/v1/cases/{case_id}/graph?focus={id}&max_hops=3&trace_id={id}`

Assigned. `max_hops` default 3, maximum 5.

```json
{
  "bounds": { "case_id": "uuid", "focus": null, "max_hops": 3 },
  "truncated": false,
  "nodes": [
    { "id": "uuid", "kind": "account", "label": "****0011", "data_classification": "synthetic" }
  ],
  "edges": [
    {
      "id": "uuid",
      "from": "uuid",
      "to": "uuid",
      "kind": "transfer",
      "assertion_kind": "verified",
      "method_version": "csv_canonical.v1",
      "amount": "100000.0000",
      "currency": "INR",
      "evidence_ids": ["uuid"]
    }
  ],
  "components": [{ "id": "c1", "node_ids": ["uuid"] }]
}
```

## Observations and relationships

### `POST /api/v1/cases/{case_id}/observations`

Assigned investigator.

```json
{
  "kind": "dns",
  "domain": "syn-a.test",
  "rrtype": "A",
  "rdata": "203.0.113.50",
  "observed_at": "2026-01-16T09:00:00Z",
  "note": "Synthetic planted observation."
}
```

201. `kind` is `dns` or `hosting`. Phase 1 does not resolve the name.

### `POST /api/v1/cases/{case_id}/observations/dns`

409 while `VAGEXA_PASSIVE_INTEL` is off. The demo leaves it off.

### `GET /api/v1/cases/{case_id}/observations`

Assigned. Observations with times and provenance ids.

### `POST /api/v1/cases/{case_id}/correlations`

Assigned investigator or analyst. 202 job, or 200 if the implementation runs
it inline because the case is small. Either way the result is the same rows.
Phase 1 may run it in the worker. The contract is the rows, not the timing.

### `POST /api/v1/relationships/{id}/confirm` and `/reject`

Assigned `lead` or `investigator` on that relationship's case. 404 otherwise.
Body optional `{ "note": "Reviewed the two observations." }`. The note becomes
an annotation. Assertion kind is unchanged.

### `GET /api/v1/cases/{case_id}/cross-case-signals`

Assigned.

```json
{
  "items": [
    {
      "identifier_kind": "account",
      "masked": "****0011",
      "other_case_count": 1,
      "assertion_kind": "inferred",
      "method": "exact_identifier",
      "limitations": "Same normalised key. Not a finding that the holders are the same person."
    }
  ]
}
```

Audit `cross_case.lookup`. No foreign title.

## Notes, copilot, report

### `POST /api/v1/cases/{case_id}/annotations`

Assigned investigator.

```json
{ "target_kind": "account", "target_id": "uuid", "body": "Two printed names. Left unresolved." }
```

201. Audit `annotation.create`.

### `GET /api/v1/cases/{case_id}/annotations`

Assigned. Cursor list.

### `POST /api/v1/cases/{case_id}/copilot/queries`

Assigned investigator or analyst.

```json
{ "tool": "trace_summary", "question": null, "mode": "deterministic" }
```

`tool` is required. Unknown tool is 422. `question` is stored and not routed.

```json
{
  "id": "uuid",
  "mode_used": "deterministic",
  "model_id": null,
  "tools": ["trace_summary"],
  "statements": [
    {
      "text": "fifo.v1 attributed 100000.0000 INR to the account ending 0011 at layer 1.",
      "assertion_kind": "verified",
      "evidence_ids": ["uuid"],
      "limitations": "Shown in a source record and allocated under horizon 3."
    }
  ]
}
```

Audit detail: tool name and bundle hash. Not the question.

### `POST /api/v1/cases/{case_id}/reports`

Assigned investigator. 200 `text/html` when a succeeded trace exists, else 409.
`ETag` is the content hash. Audit `report.export`.

### `GET /api/v1/cases/{case_id}/evidence`

Assigned. Cursor list of evidence ids, kinds, hashes, provenance ids. Not the
ground-truth file.

### `GET /api/v1/cases/{case_id}/audit`

Assigned investigator, analyst, or auditor. Cursor list of actions, times,
outcomes, request ids. Detail is the redacted detail.

## Health

`GET /health/live` and `GET /health/ready` are unauthenticated. Ready runs
`SELECT 1`. Bodies contain status and version only.
