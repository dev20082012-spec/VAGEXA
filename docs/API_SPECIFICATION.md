# API specification

The HTTP API is versioned at `/api/v1`. It is a case-centric resource API.
Interactive clients use it. They do not receive a database cursor, a Cypher
endpoint, or a SQL endpoint.

This specification is the resource index. Field-level requests, responses, and
the user and annotation routes are in [API contracts](API_CONTRACTS.md). Where
the two differ, the contracts file wins, and it must still follow the accepted
ADRs. An OpenAPI document generated from the application is checked against
the contracts file.

## Conventions

- Authentication: session cookie set by `POST /api/v1/auth/login`. No token in `localStorage`.
- Authorisation: every `/cases/{case_id}` route checks assignment after authentication. An unknown case and a case the caller cannot see both return 404.
- Content type for JSON: `application/json`. Amounts are strings with up to four decimal places, for example `"1500.0000"`.
- Times are ISO-8601 with a offset. Dates are `YYYY-MM-DD`.
- Identifiers are UUID strings.
- Errors are `application/problem+json`: `type`, `title`, `status`, `detail`, `instance`, `request_id`. Validation errors add `errors`, an array of `{ "field", "reason" }`. `detail` is safe to show. It does not include SQL, file paths, or case content the caller cannot access.
- Lists use cursor pagination: `?limit=50&cursor=`. The response is `{ "items", "next_cursor" }`. `limit` maximum is 200.
- Writes that start work return `202` with a job resource. Parsing and tracing do not run to completion inside the upload request.
- Idempotency: statement upload is idempotent on `(case_id, sha256)`.

## Authentication

| Method | Path | Effect |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Body `{ "username", "password" }`. Sets the cookie. Returns the user and roles. |
| `POST` | `/api/v1/auth/logout` | Revokes the session. |
| `GET` | `/api/v1/auth/me` | Current user, roles, and `data_mode`. |

Login failure is 401 with the same problem title for unknown user and bad password.

## Cases and complaints

| Method | Path | Who | Effect |
| --- | --- | --- | --- |
| `POST` | `/api/v1/cases` | investigator, administrator | Create a case. Body includes `reference`, `title`, `data_classification`, `opened_on`. |
| `GET` | `/api/v1/cases` | assigned roles | List cases the caller may see. |
| `GET` | `/api/v1/cases/{case_id}` | assigned | Case header, classification, counts. |
| `POST` | `/api/v1/cases/{case_id}/assignments` | administrator | Assign a user. |
| `POST` | `/api/v1/cases/{case_id}/complaints` | investigator | Add a complaint. |
| `GET` | `/api/v1/cases/{case_id}/complaints` | assigned | List complaints. |

Creating an `official` case in `synthetic` mode, or the reverse, is 422.

## Statements and jobs

| Method | Path | Effect |
| --- | --- | --- |
| `POST` | `/api/v1/cases/{case_id}/statements` | Multipart upload. `202` and a job. Duplicate hash returns `200` with the existing statement and no new job. |
| `GET` | `/api/v1/jobs/{job_id}` | Job status for a job whose case the caller can see. |
| `GET` | `/api/v1/cases/{case_id}/transactions` | Cursor list. Filters: `direction`, `rail`, `booking_date_from`, `booking_date_to`. |
| `GET` | `/api/v1/cases/{case_id}/accounts` | Accounts referenced by the case. |

The upload rejects a body over the configured limit (default 25 MB) with 413.
The transaction resource includes `line_number`, `source_file_sha256`,
`assertion` information for the counterparty resolution, and masked account
fields. `GET /api/v1/accounts/{account_id}` returns the instrument and its
observations only when the caller is assigned to at least one case that cites
that instrument. A caller who is not assigned receives 404. Field-level reveal
audit is Phase 4. Phase 1 still audits case open.

A second upload of the same bytes returns the existing file and does not parse
again. `POST /api/v1/statements/{statement_id}/reprocess` enqueues a new parse
that supersedes the previous statement. ADR 0012.

## Traces and indicators

`POST /api/v1/cases/{case_id}/traces`

```json
{
  "seed_transaction_ids": ["..."],
  "policy": "fifo",
  "policy_version": "fifo.v1",
  "max_layer": 3
}
```

Returns `202` and a job. The analytical run and the job are inserted in one
transaction, and the job payload contains the run id, so the client does not
have to guess it. When the job succeeds, `GET /api/v1/traces/{trace_id}`
returns the run metadata, flows, residuals, and the per-account conservation
result. `max_layer` above 5 is 422.

`POST /api/v1/cases/{case_id}/indicator-runs` starts `indicators.v1` for the
case window in the body. `GET /api/v1/cases/{case_id}/indicators` lists the
latest successful rows. The resource has `code`, `limitations`,
`support_transaction_ids`, `method_version`, and `assertion_kind`. It has no
guilt field.

## Graph

`GET /api/v1/cases/{case_id}/graph?focus={id}&max_hops=3`

```json
{
  "bounds": { "case_id": "...", "focus": "...", "max_hops": 3 },
  "truncated": false,
  "nodes": [
    {
      "id": "...",
      "kind": "account",
      "label": "****1234",
      "data_classification": "synthetic"
    }
  ],
  "edges": [
    {
      "id": "...",
      "from": "...",
      "to": "...",
      "kind": "transfer",
      "assertion_kind": "inferred",
      "method_version": "fifo.v1",
      "amount": "40000.0000",
      "currency": "INR",
      "evidence_ids": ["..."]
    }
  ],
  "components": [{ "id": "c1", "node_ids": ["..."] }]
}
```

`max_hops` defaults to 3 and cannot exceed 5.

## Infrastructure and correlation

| Method | Path | Effect |
| --- | --- | --- |
| `POST` | `/api/v1/cases/{case_id}/observations` | Manual domain, IP, or hosting note with provenance fields. |
| `POST` | `/api/v1/cases/{case_id}/observations/dns` | Enqueue a passive lookup for a domain already on the case. 409 when passive intel is off. |
| `GET` | `/api/v1/cases/{case_id}/observations` | Observations and their times. |
| `POST` | `/api/v1/cases/{case_id}/correlations` | Run `correlate.v1`. |
| `POST` | `/api/v1/relationships/{id}/confirm` | Investigator assigned to that relationship's case. Does not change assertion kind. 404 when the caller is not assigned. |
| `POST` | `/api/v1/relationships/{id}/reject` | Same assignment rule. |
| `GET` | `/api/v1/cases/{case_id}/cross-case-signals` | Masked identifier and counts. Full foreign case ids only if assigned. |

## Copilot and reporting

`POST /api/v1/cases/{case_id}/copilot/queries`

```json
{
  "tool": "common_beneficiaries",
  "question": "Which account is shared by the complaints?",
  "mode": "deterministic"
}
```

`tool` is required and must be one of the allow-listed names. `question` is
optional, stored on the query row, and is not used to choose the tool.

Response:

```json
{
  "id": "...",
  "mode_requested": "deterministic",
  "mode_used": "deterministic",
  "model_id": null,
  "statements": [
    {
      "text": "The normalised account ending 1234 also appears on another complaint in this case.",
      "assertion_kind": "inferred",
      "evidence_ids": ["..."],
      "limitations": "Same printed identifier. This is not a finding that the holders are the same person."
    }
  ],
  "tools": ["common_beneficiaries"]
}
```

`POST /api/v1/cases/{case_id}/reports` builds the HTML report from the latest
successful trace and returns the file. The response `ETag` is the content
hash. A case with no successful trace returns 409 rather than an empty report
that looks finished.

## Health

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health/live` | Process is up. No authentication. No dependency check. |
| `GET` | `/health/ready` | Database accepts a trivial query. 503 otherwise. |

Health bodies contain status and version. They do not contain counts of cases.

## Problem types

Use stable `type` URIs under `https://vagexa.local/problems/` until a real
public host exists. Local does not mean the API is only on localhost. It means
the problem namespace is not a public website yet.

| Status | Type slug | When |
| --- | --- | --- |
| 401 | `unauthenticated` | No session. |
| 403 | `forbidden` | Role cannot do the action. |
| 404 | `not-found` | Missing, or not visible. |
| 409 | `conflict` | Duplicate decision, intel disabled, report without a trace. |
| 413 | `payload-too-large` | Upload limit. |
| 422 | `invalid` | Schema, classification, or hop cap. |
| 500 | `internal` | Unexpected. Generic detail. |
