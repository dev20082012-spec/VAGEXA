# Hackathon remaining work

Ordered for 24 November 2026, 23:00 IST. Estimates are one engineer, focused.
Do not start the P2 list.

## Status on 2026-11-22, 19:20 IST

Done: task 1 (seed command `python -m vagexa.demo_seed`) and task 4 (trace,
indicators, and correlation run inside the seed). The backend endpoints for
task 3 exist: `/summary`, `/entities`, `/audit-events`, and the evidence
routes. Still open: tasks 2, 3 (frontend), and 5 (public URL).

## P0

| Task | Effort | Depends on | Where | Acceptance | Verify | Deploy |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Seed command for `SYN-DEMO` | 4 h | Existing ingest, trace, indicators, observations, correlation | `backend/src/vagexa/synthetic/`, one command module | One command creates the case, user assignment, statements, DNS, hosting, trace, indicators, and proposals from `HACKATHON_DEMO_SCENARIO.md` | pytest against ground truth; second run does not duplicate rows | Command is idempotent so a restart can reload the case |
| 2. Open that case by default after login | 2 h | Task 1 | `frontend/src/pages.tsx`, `App.tsx` | Judge signs in and sees `SYN-DEMO` without creating a case | Browser: login, land on the case | Same build |
| 3. Case workspace | 4 h | Task 1 APIs already exist | Case detail page | Shows synthetic banner, counts, trace status, findings, and links. No hardcoded numbers | Browser against the seeded case | None |
| 4. Run the demo checks into the seed | included in 1 | Trace and indicator services | Seed command | Horizon-3 residual and fan-in/fan-out exist before the UI loads | API read after seed, no manual POST | None |
| 5. Health and login on a public URL | 4 h | Tasks 1–3 locally | Hosting, see deployment plan | `GET /health/ready` 200 and login works on the public origin | Curl the public URL, then the browser | Required |

## P1

| Task | Effort | Depends on | Where | Acceptance | Verify | Deploy |
| --- | --- | --- | --- | --- | --- | --- |
| 6. Transaction row opens detail and narration | 2 h | Task 1 | Transactions page, existing detail API | Judge sees the `syn-a.test` narration and the source line | Click the victim debit | None |
| 7. In-app investigation summary | 3 h | Tasks 1 and 3 | New page reading summary, findings, relationships | Page quotes API text, including limitations. No PDF required | Read it next to the API JSON | None |
| 8. Graph empty-state and path highlight on the seeded case | 2 h | Task 1 | `GraphPage.tsx` | Seeded graph shows accounts, the domain, the address, and the overlap. Selecting an edge shows the explanation | Browser on desktop width | None |
| 9. Tighten first-screen copy | 1 h | Task 2 | Login and case header | First screen says what VAGEXA does and that the case is synthetic | Read the login page | None |

## P2 — after submission

Copilot, HTML/PDF export polish, live DNS, RDAP, certificates, ASN,
complaints, centrality, community detection, a blended score, and a second
database. None of these repair a missing demo case.
