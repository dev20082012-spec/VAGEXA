# Hackathon final QA report

Date: 2026-11-22. The judge session used a fresh Chrome profile against
https://vagexa-rj-demo.fly.dev. It signed in as `investigator`, opened
`SYN-DEMO`, and followed the guided walkthrough. No application code was
changed. Screenshots are in `submission/demo-assets/`.

Release status: **READY WITH DOCUMENTED LIMITATIONS**.

The deployed commit is `677b4f2` (`15-live deploy`). The dataset is
`demo.v2`, seed `20261122`.

## Release matrix

| Area | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| Application | Frontend loads | PASS | `01-login.png`. Title VAGEXA. Synthetic notice visible. |
| Application | Backend responds | PASS | Sign-in reached the dashboard. No failed API responses in the walk. |
| Database | Production database connects | PASS | `/health/ready` returned 200 and `demonstration_case` `SYN-DEMO`. |
| Database | Migrations are successful | PASS | The booted case uses the current schema, including gateway records. The migration log was not copied out of the container. |
| Database | Demonstration data persists | PASS | Verified after a machine restart in the previous deployment check. This session still saw 25 transactions. |
| Authentication | Login works | PASS | Fresh session reached the dashboard. |
| Authentication | Logout works | NOT VERIFIED | The Sign out control is visible. This session did not complete the click. |
| Authorization | Restricted access is rejected | PASS | Signed-in request for an unknown case id returned 404. |
| Investigations | Investigation list loads | PASS | Dashboard shows `SYN-DEMO`. |
| Investigations | Primary investigation opens | PASS | `03-overview.png`. |
| Financial | Transaction table loads | PASS | `04-transactions.png`. |
| Financial | Search and filters work | PASS | Search for `UTRSYN0001` hid `FAN1`. Direction "Outgoing (debit)" showed 15 debit rows, including the opening `100000.0000` payment. `15-debit-filter.png`. |
| Financial | Account activity loads | PASS | `14-accounts.png`. `****0030` incoming ₹60,000.00 and outgoing ₹40,000.00. |
| Financial | Fund-flow tracing works | PASS | `06-fund-flow.png`. `****0001` to `****0013`, `fifo.v1`, residual `outside_horizon`. |
| Financial | Findings display supporting transactions | PASS | `07-findings.png`. Fan-in and fan-out on the account ending `0030`, with support counts. |
| Graph | Graph loads real backend data | PASS | `08-network.png`. Canvas drew the statement chain and infrastructure. |
| Graph | Node selection works | NOT VERIFIED | No separate node click was made. The canvas and the selected edge panel were usable. |
| Graph | Edge selection works | PASS | The gateway edge `****0011` to `syn-a.test` was selected, classification corroborated, method `correlate.v2`. |
| Graph | Evidence relationships work | PASS | The edge panel names the gateway record and the statement rows. |
| Infrastructure | Domain observations load | PASS | `09-infrastructure.png`. `syn-a.test` and `syn-b.test`. |
| Infrastructure | IP and DNS observations load | PASS | `203.0.113.50` at two times, resolver `synthetic_fixture`. |
| Correlation | Supported correlation appears correctly | PASS | `10-unified.png`. Narration and gateway links to `syn-a.test` are corroborated and proposed. |
| Correlation | Unsupported relationship remains unverified | PASS | Shared address and shared provider are unresolved. `syn-d.test` and `syn-e.test` are contradicted. Both gateway records remain. |
| Evidence | Source records are accessible | PASS | `11-evidence.png`. `SYN-PG-0001`, amount ₹1,00,000.00, synthetic. |
| Reports | Investigation report loads | PASS | `12-report.png` after a refresh. 14 statements, 25 transactions, 6 DNS, 2 hosting notes, 3 gateway records. |
| Deployment | HTTPS works | PASS | The browser loaded the `https` origin. |
| Deployment | Independent browser access works | PASS | The Chrome session started signed out. |
| Deployment | Nested page refresh works | PASS | The report URL was reloaded and still showed `SYN-DEMO`. |
| Deployment | No localhost API references remain | PASS | The login HTML and the main JavaScript and CSS bundles do not contain `127.0.0.1`, `localhost:5173`, or `localhost:8000`. |

No row is FAIL. Logout and a separate graph-node click were not exercised.
They are not release blockers: sign-in works, and the graph edge the script
selects is the corroborated bridge.

## Not in the MVP

Live DNS, certificates, RDAP, ASN, geolocation, a copilot, and a second
investigation story are out of the frozen scope. They were not presented as
working.

## Console and network

The walk recorded no browser console errors and no HTTP error from the
application origin while the pages above were loading. `/docs` and
`/openapi.json` return the application HTML shell, not an API schema.

## Defects

No P0 defect was found. No P1 defect required a code change. Graph labels
overlap where the chain is dense. That did not block reading the selected
edge. It was left as a P2.

## Security spot check

| Check | Result |
| --- | --- |
| Password in the repository | Not present. `.env.example` is empty. |
| Public API schema | Not served. |
| Unknown case id while signed in | 404 |
| Role shown in the interface | Investigator, synthetic mode. Not an administrator. |
| Cookie on the previous public sign-in | `HttpOnly`, `Secure`, `SameSite=lax` |
| Database | Listens on localhost inside the machine only |

This is not a security certification.
