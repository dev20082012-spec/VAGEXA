# Hackathon production checklist

Checked on 2026-11-22 against `https://vagexa-rj-demo.fly.dev`.

| Item | Result |
| --- | --- |
| Public HTTPS site | Loads. Fly forces HTTPS. |
| Frontend and API on one origin | The page, `/assets/...`, and `/api/v1/...` share `vagexa-rj-demo.fly.dev`. |
| No localhost in the public page or main bundle | The login HTML, `index-BNbchKOo.js`, and `index-DE_8U91u.css` do not contain `127.0.0.1`, `localhost:5173`, or `localhost:8000`. |
| Nested route refresh | `GET /cases/<id>/report` returns the application HTML, status 200. |
| Database ready | `GET /health/ready` returns 200 and `demonstration_case` `SYN-DEMO`. |
| Process liveness | `GET /health/live` returns 200. |
| Machine check | 1 of 1 passing after the machine started. |
| Migrations | Applied during boot before the process listened. The ready case exists, so the schema accepted the seed. |
| Demonstration data | 14 statements, 25 transactions, 6 DNS rows, 2 hosting notes, 3 gateway records, 18 findings, 15 relationships. |
| Persistence across restart | After `flyctl machine restart`, ready still named `SYN-DEMO` and a new sign-in still saw 25 transactions. |
| Authentication | Sign-in returns 200 for the investigator. An anonymous summary request returns 401. |
| Cookie | `HttpOnly`, `Secure`, `SameSite=lax`, path `/`, 12 hours. |
| Role | `investigator`, not administrator. |
| CORS | Set by the start script to `https://vagexa-rj-demo.fly.dev` when Fly supplies the app name. The judge's browser uses the same origin, so it does not depend on a second site. |
| Secrets in the repo | `.env.example` has an empty password. The live password is a Fly secret. |
| API docs in production | `/docs` and `/openapi.json` are disabled when `VAGEXA_ENVIRONMENT=production`. |
| Database exposure | Postgres listens on `127.0.0.1` inside the machine. |
| Upload limit | 25 MB, unchanged. Not re-tested with a public upload. |
| Login rate limit | 10 failures per username in 15 minutes. Not deliberately exhausted on the public site. |

## Environment on the host

| Name | Demonstration value |
| --- | --- |
| `VAGEXA_DATA_MODE` | `synthetic` |
| `VAGEXA_ENVIRONMENT` | `production` |
| `VAGEXA_COOKIE_SECURE` | `true` |
| `VAGEXA_CORS_ORIGINS` | `https://vagexa-rj-demo.fly.dev` |
| `VAGEXA_DATABASE_URL` | Set at boot from the volume password. Not committed. |
| `VAGEXA_STORAGE_DIR` | `/data/storage` |
| `VAGEXA_STATIC_DIR` | `/app/static` |
| `VAGEXA_REQUIRE_DEMO` | `true` |
| `VAGEXA_PASSIVE_INTEL` | `false` |
| `VAGEXA_BOOTSTRAP_USERNAME` | Fly secret |
| `VAGEXA_BOOTSTRAP_PASSWORD` | Fly secret |
| `VAGEXA_BOOTSTRAP_DISPLAY_NAME` | `Investigator` |
| `PORT` | Set by Fly |
