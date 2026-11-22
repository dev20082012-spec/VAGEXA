# System architecture

VAGEXA is one investigation system with a relational system of record, a
case-scoped analytical layer, and a browser workspace. PostgreSQL holds facts.
Python applies versioned methods. The browser displays what those methods
return.

This document is the target architecture. No service in it is running yet.
Decisions and the options that were set aside are in [decisions](decisions/README.md).

## Context

```text
Investigator browser
        |
        | HTTPS, cookie session
        v
   VAGEXA API  ----  VAGEXA worker
        |                 |
        +--------+--------+
                 |
            PostgreSQL
                 |
            file storage (statement bytes)

Optional, outbound, and off by default:
   passive DNS resolver
   later: RDAP, certificate transparency, ASN, LLM provider
```

The investigator is the only human actor. Banks, registrars, and model
providers are external sources reached through adapters, or not reached at all
in the first slice. There is no public anonymous API.

## Runtime pieces

| Piece | Responsibility | First implementation |
| --- | --- | --- |
| Web | Case workspace, graph, upload, copilot panel | Static React build behind a reverse proxy |
| API | Authn, authz, validation, use cases, report download | FastAPI, `uvicorn` |
| Worker | Parse files, run traces, build indicator runs | Same Python package, separate process |
| PostgreSQL | Facts, jobs, sessions, audit | 16 |
| File storage | Original statement bytes addressed by storage key | Local volume in demo; object storage later |
| Passive intel | DNS observations for names an investigator submitted | Adapter, disabled when unconfigured |
| LLM | Optional narration of a tool bundle | Adapter, `none` by default |

Node.js is not a runtime in this architecture. The frontend toolchain uses it
at build time only. A separate Node API would split authorisation and evidence
rules across two languages before either language has earned that split.
[ADR 0002](decisions/0002-python-fastapi-backend.md) and
[ADR 0003](decisions/0003-react-typescript-spa.md) record that choice.

Neo4j is not a runtime in the first deployment. Case graphs fit in memory under
the hop cap. A graph database becomes a rebuildable projection only after the
trigger in [ADR 0004](decisions/0004-derived-graph-networkx.md).

## Module boundaries

```text
frontend/src
  features/*          screens and view state
  api/*               HTTP client and response types

backend/src/vagexa
  api                 routers, schemas, auth dependencies
  application         one use case per investigator action
  domain              money, assertion kinds, classification checks
  intelligence
    financial         parse coordination, FIFO, indicators
    graph             subgraph load, traversal, components
    digital           observation model for domains and addresses
    correlation       shared-identifier rules, confirm/reject
    copilot           tool router, citation check, optional narrator
  evidence            provenance, hashes, supersession, audit append
  adapters
    persistence       SQLAlchemy repositories
    parsers           CSV now, PDF later, same canonical output
    passive_intel     DNS and later RDAP/CT/ASN
    llm               optional provider
    jobs              skip-locked job claim
  worker              process loop
```

`intelligence/digital` is the product engine for domains and hosting.
`adapters` is where technical clients live. Those two names stay distinct so a
lookup client is not mistaken for an analytical rule.

### Allowed calls

- `api` calls `application` and `evidence` for the audit append that belongs to the request.
- `application` calls `domain`, `intelligence`, `evidence`, and repository ports.
- `intelligence` calls `domain` and ports. It does not import FastAPI.
- `adapters` implement ports. They do not decide whether an edge is verified.
- `frontend` calls the HTTP API only.

### Forbidden calls

- A router importing NetworkX and computing a path.
- A React component thresholding fan-out into a mule label.
- An LLM client writing rows except through the copilot use case, which writes the query audit record and nothing else.
- A parser inserting a transaction without a provenance id.

## Primary flows

### Ingest a statement

1. The API authorises the case and checks that the file's classification matches the case and the deployment data mode.
2. Bytes are stored. SHA-256 is computed. A `source_files` row is inserted.
3. A job row is inserted in the same database transaction as the file record.
4. The worker claims the job with `FOR UPDATE SKIP LOCKED`.
5. The parser returns canonical rows or a structured rejection. On rejection, the file remains stored and no transaction rows are inserted.
6. On success, transactions, extracted identifiers, and provenance rows commit together.
7. The same file hash in the same case returns the existing statement.

### Run a trace

1. The investigator confirms seed transactions. Fuzzy candidates are not seeds.
2. The use case writes an `analytical_runs` row with policy id, version, parameters, and input hash.
3. The financial engine loads the case's transactions and allocates value.
4. Flows, residuals, and findings commit together. A conservation failure rolls the analytical output back and records a failed run.
5. The graph endpoint reads those flows. It does not allocate value a second time with a different rule.

### Ask the copilot

1. The question is stored on `copilot_queries`, not in the process log and not
   in `audit_events.detail`. The audit row records the mode, the tool names,
   and the bundle hash.
2. A small classifier, implemented first as keyword and tool selection rules, chooses one or more allow-listed tools.
3. Tools run under the caller's authorisation and return records.
4. Deterministic mode formats that bundle. Assisted mode, when a provider is configured, may phrase it. The citation checker removes any evidence id the tools did not return.
5. The response, tool names, and bundle hash are stored.

### Confirm a relationship

1. Only an investigator or administrator assigned to the case may confirm.
2. Confirmation changes the relationship status and does not change `assertion_kind`. A source field is classified when the row is created, not when a person accepts it.
3. The previous status remains recoverable from the audit event.

## Authorisation model

Authentication proves who the caller is. Authorisation is a separate decision:

- role permissions describe the kind of action;
- case assignment describes which case;
- cross-case reads require assignment to each case or an explicit cross-case permission.

Object identifiers in URLs are looked up after that check. Database rows carry
`case_id` where they belong to a case, and repositories include it in the
query.

## Consistency

PostgreSQL is authoritative for accounts, transactions, observations,
relationships, evidence, and audit. Graph responses are computed from those
tables. If a projection cache is added later, it carries a projection run id
and can be deleted and rebuilt. It is never edited to correct a fact.

Jobs and the rows they create commit in the database. The API process does not
use in-memory background tasks for ingestion. Those tasks die with the process
and leave the investigator unsure whether a file was accepted.

## Configuration boundary

| Setting | Effect |
| --- | --- |
| `VAGEXA_DATA_MODE` | `synthetic` or `operational`. Rejects the other mode's primary records. |
| `VAGEXA_DATABASE_URL` | PostgreSQL connection. Present only on the server. |
| `VAGEXA_SESSION_SECRET` | Signs session cookies. |
| `VAGEXA_STORAGE_DIR` | Where original bytes go in the demo topology. |
| `VAGEXA_LLM_PROVIDER` | `none` unless a provider is deliberately configured. |
| `VAGEXA_PASSIVE_INTEL` | `off` unless a resolver is configured. |

Secrets are environment or a secret store. They are not defaulted in source.

## Failure behaviour

| Failure | Investigator-visible result |
| --- | --- |
| Unreadable CSV | File retained, job rejected, no transaction rows. |
| Conservation check fails | Trace run marked failed, no partial flows presented as a result. |
| Hop cap exceeded | Request rejected with the maximum stated. |
| Model unavailable | Deterministic answer still returned. |
| Other case not assigned | Shared-identifier count only. |
| Database down | Readiness check fails. The API does not pretend a graph exists. |

## Build and release shape

The demo release is three containers: `web`, `api`, `worker`, plus PostgreSQL.
The web container serves static files and proxies `/api` and `/health`. One
Python image can run either the API command or the worker command.

Operational deployment adds backups, a real secret store, TLS termination, and
the database roles in [Database design](DATABASE_DESIGN.md). It does not add a
second application stack.

## Current gap

The repository contains this design and no implementation. The first code
change should match the layout above and should not introduce a service this
document does not name.
