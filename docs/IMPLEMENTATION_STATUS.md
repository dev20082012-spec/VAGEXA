# Implementation status

Date: 2026-11-22. This is what the repository runs. It is not the full Phase 1
investigation slice.

## Running

- FastAPI application with configuration validation, problem responses, request
  ids, structured logs, session login, and case create, list, and retrieve.
- Alembic migration for roles, users, sessions, synthetic batches, cases,
  assignments, and append-only audit events.
- React register: sign-in, case list, open a case, case detail, statement
  upload, and a financial analysis screen.
- Statement and transfer ingestion.
- `fifo.v1`, `indicators.v1`, and `statement_walk.v1`, with findings stored
  against transaction evidence. Migration `20261122_0004`.
- A derived case graph: statement transfers, FIFO layers on those transfers,
  weakly connected components, and a hop-capped shortest path. ADR 0016.
- Investigator-supplied DNS A/AAAA and hosting notes, with overlap drawn on
  that graph. Live DNS, RDAP, and certificates are not collected.
- `correlate.v1` proposals for an exact host in a narration, a shared address,
  a shared provider string, and a shared structured reference. Review is
  confirm or reject. Assertion kind does not change.
- Tests against a local PostgreSQL database.

## Not running

The copilot and reports. Live DNS and RDAP. Cycle
labels, structuring rules, dormant-to-active rules, and a blended risk score
are not implemented. ADR 0015.

## Difference from milestone M1 wording

The approved milestone asked for the transaction append-only trigger in the
first migration. This prompt limits the schema to the investigation workflow.
The trigger function is installed and tested on `audit_events`. The
`transactions` table, and the same trigger on it, arrive with statement ingest.
The column design in the database spec is unchanged.

Cases opened from the register omit `synthetic_batch_id`. The server creates a
batch with scenario key `investigator-opened` so the synthetic classification
check still holds. A caller may still send a batch id.

The approved layout is `backend/` and `frontend/`, not `apps/web`. Node is the
frontend build tool only.

Local development on this machine uses PostgreSQL 18 because Docker is not
installed. The Compose file still names Postgres 16 for machines that have
Docker. The features used (citext, `gen_random_uuid`, triggers) exist in both.

Sessions are opaque tokens. `VAGEXA_SESSION_SECRET` is not required.
