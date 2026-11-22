# Hackathon deployment test results

Date: 2026-11-22. VAGEXA is publicly accessible at
**https://vagexa-rj-demo.fly.dev**.

## 1. Hosting architecture

One Fly machine runs the production frontend and the API in one process.
PostgreSQL 16 runs in the same image and listens only on localhost. Both the
database files and the statement-byte directory are on the encrypted volume
mounted at `/data`.

## 2. Providers

| Role | Provider | State |
| --- | --- | --- |
| Application and TLS | Fly.io app `vagexa-rj-demo` | Deployed. Machine `78135d2c070608` started, check passing. |
| Region | `sin` (Singapore) | Mumbai is not offered. |
| Database | PostgreSQL 16 inside the image | Ready. Not published. |
| Volume | `vagexa_data`, 1 GB, encrypted | Created. Snapshots scheduled. |
| CI | None | Deployed with `flyctl deploy` from this workstation. |
| Local Docker | Not installed | The image was built by Fly's remote builder. |

## 3. Frontend public URL

https://vagexa-rj-demo.fly.dev

## 4. Backend public URL

Same origin. Health: https://vagexa-rj-demo.fly.dev/health/ready

There is no separate public API host. The database has no public address.

## 5. Database persistence

The volume survived a machine restart. Ready still reported `SYN-DEMO`. A new
sign-in still returned 25 transactions.

## 6. Migrations

`alembic upgrade head` runs before the server listens. The booted case
accepted the current schema, including gateway records. The migration command
itself was not copied out of the container log line by line.

## 7. Environment

Production values are in [Production checklist](HACKATHON_PRODUCTION_CHECKLIST.md).
The bootstrap password is a Fly secret. It was not printed during import.
`.env.example` still has an empty password.

## 8. Authentication

A new HTTPS session signed in as `investigator` with role `investigator`.
The session cookie is `HttpOnly`, `Secure`, and `SameSite=lax`. An anonymous
request for the case summary returned 401. Authentication was not disabled.

## 9. File storage

The evidence opened for the corroborated gateway link came from the API:
one gateway record and two transactions, each marked `synthetic`. Those rows
are in PostgreSQL. Original statement bytes also go to `/data/storage` on the
volume. No extra object store was added.

## 10. HTTPS and CORS

The browser loaded `https://vagexa-rj-demo.fly.dev/login` with a valid Fly
certificate path (the page loaded, and the cookie is marked `Secure`).
CORS is restricted to this origin. The public JavaScript does not call
localhost.

## 11. Health checks

| Request | Result |
| --- | --- |
| `GET /health/live` | 200, `{"status":"live","version":"0.1.0"}` |
| `GET /health/ready` | 200, `demonstration_case` `SYN-DEMO` |
| Fly machine check | 1 passing |

## 12. Independent browser

An independent browser opened `https://vagexa-rj-demo.fly.dev/login`. The
page title was VAGEXA. It showed the sign-in form and the sentence "This
deployment holds synthetic demonstration data only. Nothing shown is an
official record."

The signed-in investigation screens were then exercised over HTTPS with a
new session, not with a cookie already stored in a developer browser. The
click-through of the graph canvas in that browser was not repeated after
sign-in. The graph payload was loaded from the public API in that new session:
34 nodes and 30 edges.

## 13. Investigation workflow

From the public API, after sign-in:

| Step | Result |
| --- | --- |
| Dashboard data | `SYN-DEMO`, synthetic, open |
| Transactions | 25 |
| Fund-flow trace | `fifo.v1`, three hops of `100000.0000` ending at `****0013`, residual `outside_horizon` |
| Findings | `FAN_IN` and `FAN_OUT` on `****0030` |
| Infrastructure | 6 DNS rows, 2 hosting notes |
| Unified correlation | `syn-a.test` corroborated; `syn-d.test` and `syn-e.test` contradicted; 2 overlaps |
| Graph | 34 nodes, 30 edges |
| Evidence | Gateway record and two transactions, all `synthetic` |
| Report route | The public HTML shell loads for a nested report path |

Counts match the local ground truth from the previous phase.

## 14. Restart

`flyctl machine restart 78135d2c070608` completed, and the check passed.
Ready still named `SYN-DEMO`. A following sign-in still saw 25 transactions
and the `outside_horizon` residual.

## 15. Limitations

- One shared-CPU machine in Singapore, left running so a judge is less likely to wait for a cold start. That can cost money on the Fly account.
- Postgres is a single copy on one volume, not a managed cluster.
- The first boot failed because Postgres could not create its log on the root-owned volume. The log path is now `/tmp/postgres.log`. The replacement image is the one that is live.
- A signed-in click across the graph canvas was not repeated in the browser. The public API returned the graph.

## 16. P0 blockers

None remain for public access. The site answers, the demonstration case is
present, and sign-in works.

## 17. Manual action

None is required before sending the URL. For the submission form, use:

- Address: `https://vagexa-rj-demo.fly.dev`
- Username: `investigator`
- Password: the existing local bootstrap password. It is not stored in the repository.

## 18. Public access

VAGEXA is publicly accessible at https://vagexa-rj-demo.fly.dev.
