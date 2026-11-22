# 0005. A PostgreSQL job table is the first queue

- Status: accepted
- Date: 2026-11-22

## Context

Statement parsing and tracing must survive an API process restart. The
investigator also needs a job status they can reload. In-process FastAPI
background tasks do not provide that.

Redis with Celery or RQ is a normal choice and adds a service that the first
deployment does not otherwise need. The expected volume for a case-oriented
demo is small.

## Decision

Jobs are rows in PostgreSQL. The worker claims them with
`FOR UPDATE SKIP LOCKED`. Payloads contain identifiers. The API returns `202`
with the job id. Retries increment `attempts` up to a small fixed maximum,
then the job is `failed` with an error code.

Redis is not part of the first compose file.

## Consequences

- The job and the source-file row commit together.
- A stuck lock needs a timeout in the worker so a dead process does not hold a
  job forever. The first timeout is part of the worker implementation.
- A later move to Redis is an ADR if the polling worker cannot keep up. The
  use cases should depend on a queue port so that move does not reach into the
  financial engine.

## Alternatives

- Celery and Redis. Capable. Extra operational surface. Rejected for Phase 1.
- A cron script that scans a folder. Harder to authorise and to report status.
  Rejected.
