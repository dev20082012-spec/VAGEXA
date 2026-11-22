# Deployment architecture

The first deployable shape is a single machine running containers. It is enough
for development and for a synthetic hackathon demonstration. It is not the
shape in which official records should be stored. That step is Phase 4 in the
roadmap.

## Environments

| Environment | Data mode | Who uses it | Records |
| --- | --- | --- | --- |
| Local | `synthetic` | Developers | Generated scenarios only |
| Demo | `synthetic` | Supervised demonstration | The same scenarios, or a fresh generated batch |
| Operational | `operational` | Authorised investigators, later | Official records. Not part of the hackathon deploy. |

Each environment has its own database and its own storage directory. Restoring
a demo dump into an operational database is a release-blocking mistake. The
mode flag is a second barrier, not the only one.

## Demo topology

```text
browser
   |
   v
web container
   static React files
   proxies /api and /health to the API
   |
   +--> api container     VAGEXA_DATA_MODE=synthetic
   |
   +--> worker container  same image, worker command
   |
   +--> postgres:16
   |
   file volume mounted on api and worker
```

One Docker Compose file should describe this when implementation starts. It is
not in the repository yet. Images are built from the repository. PostgreSQL
data and statement bytes live in named volumes, not in the image.

The API and the worker use the same image and different commands:

- API: `uvicorn vagexa.api.main:app`
- Worker: `python -m vagexa.worker`

There is no Redis, no Neo4j, and no separate Node server in this topology.
The web image contains compiled static files. Node is a build tool inside the
image build, not a running service.

## Configuration

| Variable | Local / demo | Notes |
| --- | --- | --- |
| `VAGEXA_DATA_MODE` | `synthetic` | Required. The process refuses to start if it is missing. |
| `VAGEXA_DATABASE_URL` | Compose network hostname | Not baked into the image. |
| `VAGEXA_SESSION_SECRET` | Unique per environment | Required. No source default. |
| `VAGEXA_STORAGE_DIR` | Volume path | Original statement bytes. |
| `VAGEXA_LLM_PROVIDER` | `none` | Assisted mode stays off. |
| `VAGEXA_PASSIVE_INTEL` | `off` | Scenario observations are preloaded. |
| `VAGEXA_UPLOAD_MAX_BYTES` | `25000000` | Matches the API limit. |
| `VAGEXA_LOG_LEVEL` | `info` | Structured JSON to stdout. |

Compose passes these from an env file that is gitignored. An example file may
list the names with empty values. It must not contain a usable secret.

## Network

- Only the web container publishes a host port.
- PostgreSQL is not published to the host in the demo compose, except a
  developer override that is not the default.
- Outbound traffic from the worker is unnecessary while passive intel and the
  LLM are off. A demo that enables either one should say so in the run notes.

## Observability

Phase 1: JSON logs with request ids, `/health/live`, and `/health/ready`.
Log aggregation is the host's container logs.

Phase 4, before operational use: ship those logs to a collector, add metrics
for job failures and ingest counts, and keep account numbers out of metric
labels. OpenTelemetry is the intended instrumentation API when that work
starts. It is not a dependency of the first skeleton unless the skeleton can
add it without delaying the evidence triggers and tests.

## Backups

Demo volumes may be deleted. That is acceptable because they hold synthetic
data that can be regenerated.

Operational backups are a precondition of storing official records:

- daily database dump or volume snapshot, retained under the policy the
  organisation sets;
- statement-byte volume included;
- one restore rehearsal recorded;
- backup media encrypted and access-limited.

No retention period is invented here. It is an unresolved organisational
decision.

## Identity in production

The demo uses local accounts and Argon2id. Operational deployment is expected
to use the organisation's OIDC provider. The application should keep session
establishment behind an authenticator interface so the case tables do not
change when that happens. Building OIDC is Phase 4. Designing the interface is
part of the first auth use case, so the local implementation is not hard-wired
through every route.

## What a hackathon machine needs

A current Docker engine, the compose file once it exists, the env file, and
the command that loads `ring-01`. It does not need API keys. If the machine is
shared, the demo user accounts are created by a documented bootstrap command
and the passwords are chosen at runtime, not committed.

## Shutdown

Stopping the compose project leaves volumes in place until someone removes
them. A documented `down` for the demo should tell the operator whether volumes
will be kept. Deleting volumes is acceptable only in `synthetic` mode.
