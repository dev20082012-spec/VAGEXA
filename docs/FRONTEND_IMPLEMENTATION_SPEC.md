# Frontend implementation specification

Vite, React, TypeScript, React Router, TanStack Query. The client renders
server results. It does not allocate money, count fan-in, or call a model
vendor. Amounts stay strings. Assertion kind is a word plus a line pattern:
solid verified, dashed inferred, dotted hypothesis. Colour is not the only
encoding.

Feature folders under `frontend/src/features/`. HTTP types under
`frontend/src/api/`. A case switch clears the previous case's queries from
the rendered tree.

Every case screen shows the classification banner. In this release it reads
`synthetic`.

## 1. Login

| | |
| --- | --- |
| Purpose | Start a session. |
| Actions | Submit username and password. |
| Data | None until success. |
| API | `POST /api/v1/auth/login` |
| Components | Form, error text. |
| Loading | Disable submit. |
| Empty | The form. |
| Error | 401 shows one sentence for bad credentials. No distinction. |
| Permission | Public. |

## 2. Case list

Called the investigation dashboard because a case is the investigation. It is
a list, not a chart of suspicion.

| | |
| --- | --- |
| Purpose | Open an assigned case. |
| Actions | Open a row. Investigators may start "New case". |
| Data | Reference, title, classification, status. |
| API | `GET /api/v1/cases`, `POST /api/v1/cases` |
| Components | Table, banner, create form. |
| Loading | Skeleton rows. |
| Empty | "No assigned cases." |
| Error | Problem detail. |
| Permission | The list is already filtered. Create requires investigator or administrator. |

## 3. Case workspace

| | |
| --- | --- |
| Purpose | The spine of the journey: counts, seeds, residuals, links to the other screens. |
| Actions | Choose seeds, start a trace, read residuals, jump to graph, transactions, infrastructure, report. |
| Data | Case header, latest trace summary, indicator counts, overlap count. |
| API | Case, latest trace, indicators, observations. |
| Components | Banner, residual panel, action row. |
| Loading | Panels independently. |
| Empty | "No statement loaded" with the upload action. |
| Error | A failed trace shows `status=failed` and no flows. |
| Permission | Assigned roles. Analysts do not see upload or confirm. |

The residual panel uses the reason code `outside_horizon` in words. It does
not say "final beneficiary".

## 4. Transaction explorer

| | |
| --- | --- |
| Purpose | Read normalised rows and open the source line. |
| Actions | Filter direction, rail, and dates. Select seeds. Upload CSV. |
| Data | Transaction items from the contract, file hash, line number. |
| API | Transactions, statement upload, job poll. |
| Components | Filter bar, table, upload form with subject account and IFSC or VPA. |
| Loading | Table placeholder. Job status text while parsing. |
| Empty | Upload form. |
| Error | 422 field errors on the form. Job `rejected` shows the error code. |
| Permission | Read: assigned. Upload: investigator. |

Holder names for an account are a list of observations, not one cell.

## 5. Network graph

| | |
| --- | --- |
| Purpose | Inspect statement edges and, after a run, FIFO edges. |
| Actions | Set focus, set hops 1–5, select an edge, read its evidence. |
| Data | Graph payload. |
| API | `GET .../graph` |
| Components | Cytoscape canvas, legend with the three words, edge inspector, residual callout. |
| Loading | Canvas placeholder. |
| Empty | "No accounts in this case." |
| Error | 422 when hops exceed 5, shown before the request if the control enforces it. |
| Permission | Assigned. |

The inspector shows amount, assertion kind, method version, and evidence
links. It does not show a rank.

## 6. Infrastructure

| | |
| --- | --- |
| Purpose | Record a domain, an address, and a hosting note, and read overlap. |
| Actions | Submit an observation. Read the limitation. |
| Data | Observations and overlap relationships. |
| API | Observations, relationships. |
| Components | Form, observation list with timestamps, limitation quote. |
| Loading | List placeholder. |
| Empty | Form plus "No observations." |
| Error | Validation on the domain or IP. |
| Permission | Read: assigned. Write: investigator. There is no "look up live DNS" button in the demo. |

## 7. Evidence viewer

| | |
| --- | --- |
| Purpose | From any evidence id, show kind, hash, provenance, and the source line. |
| Actions | Open an id. Read both holder observations when they conflict. |
| Data | Evidence, provenance, transaction or observation. |
| API | Evidence list and the object routes. |
| Components | Stacked source, normalised, and derived sections. |
| Loading | One section at a time. |
| Empty | "This claim has no evidence id" is an error state, not a normal empty page. |
| Error | 404. |
| Permission | Assigned. |

Contradicting observations are shown together and labelled unresolved. The
screen does not offer "pick the true name" in Phase 1.

## 8. Copilot

| | |
| --- | --- |
| Purpose | Run one named tool and read cited statements. |
| Actions | Choose `summarize_case`, `trace_summary`, `list_indicators`, `common_beneficiaries`, `infrastructure_for_case`, or `list_evidence`. Optional text is stored. |
| Data | Tool response. |
| API | `POST .../copilot/queries` |
| Components | Tool buttons, optional text area, statement list with evidence links. |
| Loading | Disable the chosen button. |
| Empty | Before a trace, `trace_summary` shows the reason `no_successful_trace`. |
| Error | 422 unknown tool. |
| Permission | Assigned investigator or analyst. |

There is no free-text send button that runs a trace. The optional text is
labelled "stored with this query" and is not required.

## 9. Report

| | |
| --- | --- |
| Purpose | Download the HTML report for the latest succeeded trace. |
| Actions | Export. |
| Data | The file. |
| API | `POST .../reports` |
| Components | Export button, 409 explanation. |
| Loading | Button busy. |
| Empty | 409 "No succeeded trace." |
| Error | Problem detail. |
| Permission | Assigned investigator. |

## 10. Access management

| | |
| --- | --- |
| Purpose | Create users and assignments. |
| Actions | Create user, disable user, assign a case role. |
| Data | User list, case reference the administrator types or selects from cases they... they may not be assigned. The assignment form takes a case reference. If they cannot read the case, the API still accepts the assignment because that route is a global administrator power. The form does not preview the narrative. |
| API | Users and assignment routes. |
| Components | User table, create form, assignment form. |
| Loading | Table placeholder. |
| Empty | "No users yet" is unlikely after bootstrap. Show the table. |
| Error | 403 for a non-administrator. 409 duplicate username. |
| Permission | Global administrator only. |

## Shared states

A 401 anywhere redirects to login. A 404 on a case route shows "This case is
not available." It does not say whether the case exists.
