# Hackathon live deployment

Verified on 2026-11-22. The public site is:

**https://vagexa-rj-demo.fly.dev**

The API is on the same origin. `GET /health/ready` returns 200 and
`"demonstration_case": "SYN-DEMO"`.

## Architecture

| Piece | What is running |
| --- | --- |
| Host | Fly.io app `vagexa-rj-demo`, personal organisation, region `sin` (Singapore). Mumbai is not in the current region list. |
| Public address | `https://vagexa-rj-demo.fly.dev`. Fly terminates TLS. Shared IPv4 `66.241.124.233`. Dedicated IPv6 `2a09:8280:1::21b:2746:0`. |
| Frontend | Vite production build, served by the API from `/app/static`. A nested path such as `/cases/.../report` returns the application shell. |
| API | `uvicorn vagexa.api.main:create_app --factory` on `0.0.0.0` and the platform port. |
| Database | PostgreSQL 16 in the same image. It listens on `127.0.0.1` only. |
| Volume | `vagexa_data` (`vol_40oy9gwznegqomm4`), 1 GB, encrypted, mounted at `/data`. Scheduled snapshots are on, with 5 retained. |
| Statement bytes | `/data/storage` on that volume. The evidence shown in the app is also stored in PostgreSQL. |
| Mode | `synthetic` |
| Machine | `78135d2c070608`, `shared-cpu-1x`, 1 GB memory. `auto_stop_machines` is off, so one machine stays running. |

Configuration is `fly.toml` at the repository root. The image is
`deploy/Dockerfile`. `deploy/start.sh` starts Postgres, runs
`alembic upgrade head`, then `python -m vagexa.deploy_boot`. That boot
creates the investigator only when the username is missing and loads
`SYN-DEMO` again without inserting a second copy. It does not drop or
truncate the database.

## Secrets

`VAGEXA_BOOTSTRAP_USERNAME`, `VAGEXA_BOOTSTRAP_PASSWORD`, and
`VAGEXA_BOOTSTRAP_DISPLAY_NAME` are Fly secrets. They are not in the image
or the repository. The database password is generated on the volume at first
boot and is not printed.

## Restart

The machine was restarted with `flyctl machine restart`. It became healthy
again. `GET /health/ready` still reported `SYN-DEMO`, and a new sign-in still
saw 25 transactions.

## Limits

- One machine in Singapore. Fly does not promise uninterrupted uptime.
- Leaving the machine running can incur a charge on the Fly account. After the submission window, `flyctl scale count 0 --app vagexa-rj-demo` stops it without deleting the volume.
- PostgreSQL is not a managed multi-node database. It is not reachable from the internet.
- The health-check grace period on this Fly plan is capped at one minute. The current boot finishes inside that window.
- Login rate limiting is 10 failures for the same username in 15 minutes.

## Recovery

Logs: `flyctl logs --app vagexa-rj-demo`.

Status: `flyctl status --app vagexa-rj-demo`.

A failed release can be replaced by deploying an earlier image:

```powershell
flyctl releases --app vagexa-rj-demo
flyctl deploy --image <registry-image> --app vagexa-rj-demo
```

Do not destroy `vagexa_data` to recover the demonstration. If `SYN-DEMO` is
missing but the volume is intact, restarting the machine runs the idempotent
seed again. If `/data/pg` exists and `/data/db_password` does not, the start
script stops and refuses to create a new database over the old files.

Redeploy from the repository root:

```powershell
flyctl deploy --ha=false --app vagexa-rj-demo
```

`--ha=false` matters. A second machine would not have this volume.
