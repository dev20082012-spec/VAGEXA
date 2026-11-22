# VAGEXA submission notes

VAGEXA is a proprietary investigation workspace for authorised users. It keeps
financial records, infrastructure observations, and the evidence for each
proposed link in one case. A lead is not a finding of guilt.

The problem statement is **Financial Crime Infrastructure & Money-Trail
Analysis System**, from the Rajasthan Police Hackathon 2026 site
(https://rajasthanpolicehackathon.in/).

## Prototype

https://vagexa-rj-demo.fly.dev

Sign in as `investigator`. The password is supplied with the submission and
is not in this repository. Open `SYN-DEMO` and choose **Start the guided
walkthrough**. The sequence is written in
`docs/HACKATHON_FINAL_DEMO_SCRIPT.md`.

The case is synthetic. Accounts, domains, addresses, and gateway records are
fictional.

## What the prototype does

- Loads bank-statement rows and shows them with decimal amounts, not floating-point totals.
- Traces one opening payment three hops with `fifo.v1` and leaves the remainder `outside_horizon`.
- Matches fan-in and fan-out on one account with `indicators.v1`, and states that a rule match is not guilt.
- Stores DNS and hosting observations with the observation time and source.
- Proposes a financial-to-domain link only from a stored gateway record and a narration, using `correlate.v2`.
- Keeps a shared address as unresolved, and keeps two disagreeing gateway records as contradicted.
- Draws those stored rows in one graph and opens the source record for the selected edge.
- Builds the report from the same API responses, including the limitations.

## Architecture that is actually running

| Part | Implementation |
| --- | --- |
| Browser | React and TypeScript, built with Vite. One production bundle. No database URL or model key. |
| Server | Python, FastAPI, and Uvicorn. The same process serves the built pages and the API. |
| System of record | PostgreSQL 16 on a private volume. Not reachable from the internet. |
| Financial rules | `fifo.v1` and `indicators.v1`, in tested domain modules. |
| Graph | NetworkX builds a derived view for the case. It is not a second database. |
| Infrastructure | Investigator-supplied DNS and hosting rows. No live lookup on this host. |
| Correlation | `correlate.v2`. Display labels are computed when the case is read. |
| Evidence | Source rows stay stored. Findings cite them and include a limitation. |

The host is one Fly.io machine in Singapore, app `vagexa-rj-demo`, commit
`677b4f2`.

## Screenshots

`submission/demo-assets/` holds the fresh-session captures: sign-in,
dashboard, overview, transactions, search, fund flow, findings, network,
infrastructure, unified intelligence, evidence, report, account totals, and
the outgoing filter.

## Limits

Live DNS, certificates, a copilot, and operational casework are not part of
this deployment. The public event page also asks for an action-plan
presentation and a wireframe. Those files are not in this directory. The
copyright owner in the repository is still a placeholder, and the licence
remains All Rights Reserved.

The verification record is `docs/HACKATHON_FINAL_QA_REPORT.md`.
