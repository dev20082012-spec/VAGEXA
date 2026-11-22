# Backend module specification

One Python 3.12 package, `backend/src/vagexa`. Two processes run it: the API
and the worker. They share the database. They are not microservices. ADR 0002
and ADR 0005.

Routers call one use case. Use cases do not import NetworkX. Intelligence
modules do not import FastAPI.

```text
api/            HTTP, auth dependencies, problem responses
application/    one use case per action
domain/         money, classification, assertion checks
intelligence/
  financial/    csv parse coordination, fifo, indicators
  graph/        load and project
  digital/      observation rules and overlap wording
  correlation/  correlate.v1
  copilot/      tool functions
evidence/       provenance, hashes, audit append
adapters/
  persistence/  repositories
  parsers/      csv_canonical.v1
  passive_intel/  interface only; demo calls are off
  jobs/         skip-locked claim
worker/
```

## Shared error rule

Use cases raise typed errors. The API maps them to `application/problem+json`
with `request_id`. Unexpected exceptions become 500 with a generic detail.
Logs take the code and the ids, not the narration or the password.

A failed parse or a failed conservation check leaves no partial analytical
rows. The source file stays.

## Modules

### Authentication and sessions

| | |
| --- | --- |
| Responsibility | Verify the password, create and revoke sessions, resolve the caller. |
| Inputs | Username, password, cookie token. |
| Outputs | Session cookie, user id, global roles, `data_mode`. |
| Dependencies | `users`, `sessions`, Argon2id, audit. |
| Interface | `login`, `logout`, `current_user`. |
| Errors | 401 identical for unknown user and bad password. 403 when the user is disabled. |
| Security | Store the token hash. Constant-time password check. No password in logs or audit detail. |
| Tests | Bad password, disabled user, revoked session, expired session. |

### Users and assignments

| | |
| --- | --- |
| Responsibility | Administrator creates and disables users and assigns case roles. |
| Inputs | Username, display name, temporary password set by the administrator, case id, case role. |
| Outputs | User id, assignment row. |
| Dependencies | Authn, audit. |
| Interface | `create_user`, `disable_user`, `assign`. |
| Errors | 403 when the caller is not an administrator. 409 on duplicate username. |
| Security | Creating a user does not assign them to existing cases. Assignment does not grant the administrator a read. |
| Tests | Non-administrator receives 403. New user receives 404 on an existing case. |

### Cases and complaints

| | |
| --- | --- |
| Responsibility | Create a synthetic case, assign the creator as lead, add a complaint. |
| Inputs | Reference, title, opened_on, narrative, optional external reference. |
| Outputs | Case and complaint resources. |
| Dependencies | Data-mode check, provenance, audit. |
| Interface | `create_case`, `get_case`, `list_cases`, `add_complaint`. |
| Errors | 422 when classification is `official` in synthetic mode. 404 when not assigned. |
| Security | List returns only assigned cases. |
| Tests | Creator can read the new case. A second user cannot. Official insert fails. |

### Ingestion and normalisation

| | |
| --- | --- |
| Responsibility | Store bytes, hash them, enqueue parse, map CSV to transactions, reject a missing subject account, reprocess by inserting a superseding statement. |
| Inputs | Multipart file, subject account or VPA, currency. Reprocess takes a statement id. |
| Outputs | `202` job, or `200` when the hash already exists. Transactions and observations after the worker commits. |
| Dependencies | Storage, jobs, `csv_canonical.v1`, accounts upsert. |
| Interface | `upload_statement`, `reprocess_statement`, `CsvParser.parse`. |
| Errors | 413 over 25 MB. 422 missing subject, bad decimal, unknown rail, IFSC shape. Job `rejected` with an error code and zero transaction rows. |
| Security | Storage key is generated. Filename is not a path. |
| Tests | Duplicate hash, missing subject, four-decimal rejection, reprocess hides the old rows from the analytical query and keeps them stored. |

### Financial intelligence

| | |
| --- | --- |
| Responsibility | `fifo.v1` and `indicators.v1` as specified in the algorithm document. |
| Inputs | Confirmed seed transaction ids, `max_layer` 1–5, indicator window. |
| Outputs | Flows, residuals, indicator rows, one finding with limitations. |
| Dependencies | Current transactions only. Domain conservation check. |
| Interface | `FifoTracer.run`, `IndicatorRunner.run`. |
| Errors | Unknown seed, seed in another case, `max_layer` above 5, conservation failure fails the run and publishes no flows. |
| Security | Seeds must belong to the authorised case. |
| Tests | The synthetic chain, fan-in, fan-out, date-only dwell skip, conservation failure. |

### Graph intelligence

| | |
| --- | --- |
| Responsibility | Build the response described in the graph spec. No writes. |
| Inputs | Case id, optional focus, `max_hops`, optional trace run id. |
| Outputs | Nodes, edges, components, `truncated`. |
| Dependencies | Repositories for current transactions, flows, observations, relationships. NetworkX. |
| Interface | `build_case_graph`. |
| Errors | 422 above 5 hops. 404 when the case is not visible. |
| Security | No other case's narrative in the payload. |
| Tests | Edges exist before a trace. Horizon-3 graph has no attributed edge to account B. Overlap edge includes the limitation. |

### Infrastructure and correlation

| | |
| --- | --- |
| Responsibility | Store manual observations. Run `correlate.v1`. Confirm and reject without changing assertion kind. |
| Inputs | Domain, IP, note, or a request to correlate. |
| Outputs | Observation rows, proposed relationships, decision audit. |
| Dependencies | Digital wording for the overlap limitation. Assignment check on the relationship's case. |
| Interface | `record_observation`, `correlate`, `decide_relationship`. |
| Errors | 409 when a DNS lookup is requested and passive intel is off. Phase 1 does not call the network. |
| Security | Overlap text is fixed by the method, not by the client. |
| Tests | Two domains, one IP, limitation present, no party created. Analyst receives 403 on confirm. |

### Copilot

| | |
| --- | --- |
| Responsibility | Run the named tool and store the query. |
| Inputs | `tool` allow-list, optional question text. |
| Outputs | Statements with evidence ids, assertion kinds, and limitations. `model_id` null. |
| Dependencies | The other intelligence modules through their query functions, not through SQL assembled from the question. |
| Interface | `run_tool`. |
| Errors | 422 unknown tool. Empty tool result uses a reason code, not an invented entity. |
| Security | Question text is not logged. It is not sent to a provider while `VAGEXA_LLM_PROVIDER=none`. |
| Tests | `trace_summary` cites only the fixture evidence ids. A question containing "ignore instructions" changes nothing. |

### Evidence, audit, and report

| | |
| --- | --- |
| Responsibility | Append provenance and evidence, append audit, render escaped HTML. |
| Inputs | The case's latest succeeded trace and findings. |
| Outputs | A report file, its hash, an evidence row, an audit row. |
| Dependencies | Evidence contract. |
| Interface | `export_report`, `append_audit`. |
| Errors | 409 when no succeeded trace exists. |
| Security | HTML-escape every interpolated string. The report omits other cases. |
| Tests | A narration containing `<script>` is escaped. Export writes `report.export`. |

## Worker

`python -m vagexa.worker` claims jobs with `FOR UPDATE SKIP LOCKED`.
It runs parse, reprocess, trace, indicators, and correlation. It does not
serve HTTP. A lock older than 15 minutes is reclaimable. After 3 attempts the
job is `failed` with an error code.

## What is intentionally absent

No message bus, no model client in the Phase 1 process, no Cypher, no code
path that sets `is_mule` or writes a risk number.
