# Hackathon deployment plan

Live at https://vagexa-rj-demo.fly.dev. Verified on 2026-11-22. The local
API on `127.0.0.1:8000` is not the submission. The result is in
[Deployment test results](HACKATHON_DEPLOYMENT_TEST_RESULTS.md).

`deploy/Dockerfile` and `deploy/start.sh` build one image: the static
investigator app, the API, and PostgreSQL 16. The database listens on
localhost inside that image. A Fly volume at `/data` is where the database
and statement files are meant to persist. `deploy/docker-compose.yml` still
starts only a local Postgres and is not the public host. This workspace's
database is PostgreSQL 18 on `127.0.0.1:5433`. Docker is not installed here.
The image is built by Fly's remote builder, so local Docker is not required.
The live configuration is `fly.toml` in the repository root.

## Target

One small Linux VM or a two-service host.

| Piece | Choice |
| --- | --- |
| API | The existing FastAPI process, `uvicorn vagexa.api.main:create_app --factory`, port 8000, bound to localhost on the VM |
| Frontend | `npm run build`, static files behind the same HTTPS host. Proxy `/api` and `/health` to the API. Do not put the database URL in the frontend |
| Database | Managed Postgres 16, or Postgres in the existing Compose file on the VM. One volume. Do not use SQLite |
| Mode | `VAGEXA_DATA_MODE=synthetic` |
| Cookie | `VAGEXA_COOKIE_SECURE=true` behind HTTPS |
| CORS | The public origin only |
| Lookup | `VAGEXA_PASSIVE_INTEL` unset or false |
| Storage | A persistent directory for `VAGEXA_STORAGE_DIR`. Statement bytes live there |
| Demo data | After migrate, run the `SYN-DEMO` seed. It must be safe to run again |
| Health | `GET /health/ready` checks the database. Use it as the process check |
| Secrets | Database URL and the bootstrap password only in the host environment. They are not in git |

## Not in this plan

Kubernetes, a second graph database, a worker farm, and a custom domain
beyond whatever the host provides. A platform subdomain is enough.

## Proof it is deployed

From a network that is not this PC:

1. `GET /health/ready` returns 200.
2. The login page loads over HTTPS.
3. The seeded investigator opens `SYN-DEMO`.
4. Transactions, the residual, the indicator, the DNS overlap, and the
   narration proposal are present without an upload.
5. Restart the API process and repeat step 3. The case is still there.

Until those five pass, the deployment status is "not submitted".
