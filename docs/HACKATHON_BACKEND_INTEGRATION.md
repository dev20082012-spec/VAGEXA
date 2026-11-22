# Hackathon backend integration

Date: 2026-11-22. This is the backend that powers `SYN-DEMO`. It is not a
claim that the whole platform is complete.

## Data flow

1. `python -m vagexa.demo_seed --username <existing investigator>` loads the
   case through the normal services: ingest, DNS and hosting observations,
   one gateway record, then `fifo.v1`, `indicators.v1`, and `correlate.v2`.
2. The investigator signs in. Every route checks the session, the CSRF token
   on writes, and the case assignment. An unassigned caller receives 404.
3. The workspace reads the bounded summary, then the existing transaction,
   trace, indicator, observation, relationship, and graph routes.
4. Any finding or graph edge lists `support` items. Each item opens with the
   evidence route and returns the stored source row with its provenance.

## Module boundaries

| Module | Role | New in this change |
| --- | --- | --- |
| `intelligence/financial` | FIFO, indicators, activity | No |
| `intelligence/graph/build.py` | Derived graph | `support` on every edge |
| `intelligence/correlation/correlate.py` | Matching rules | `gateway_merchant`, version `correlate.v2` |
| `intelligence/correlation/classify.py` | Six display labels from stored rows | Yes |
| `application/bridge_service.py` | Gateway records | Yes |
| `application/investigation_service.py` | Summary, entities, audit list, evidence | Yes |
| `demo_seed.py`, `synthetic/demo.py` | Idempotent demo loader and hand-written ground truth | Yes |
| `api/deps.py` | Database session | Commits before the response (`scope="function"`) |

## Endpoints the demo uses

| Endpoint | Returns |
| --- | --- |
| `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | Session and CSRF token |
| `GET /api/v1/cases` | Cases the caller is assigned to |
| `GET /api/v1/cases/{id}/summary` | **New.** Case, synthetic notice, counts, latest trace and residuals, indicator codes, relationship counts by classification, up to 10 key relationships, last 10 audit actions, limitations |
| `GET /api/v1/cases/{id}/entities` | **New.** Accounts (masked), domains, IP addresses, each bounded to 200 |
| `GET /api/v1/cases/{id}/audit-events` | **New.** Last 50 actions, outcome, time. No detail payload |
| `GET /api/v1/cases/{id}/transactions` | Existing. Filters and pages of at most 100 |
| `GET /api/v1/cases/{id}/financial-summary`, `/activity` | Existing |
| `GET /api/v1/traces/{id}` | Existing, plus `reference` per hop and `path_summary` |
| `GET /api/v1/cases/{id}/indicators`, `/findings` | Existing |
| `GET /api/v1/cases/{id}/observations` | Existing |
| `GET /api/v1/cases/{id}/gateway-records` | **New.** Gateway rows as source records |
| `POST /api/v1/cases/{id}/gateway-records` | **New.** Investigator adds one. Idempotent on `source_record_id` |
| `GET /api/v1/cases/{id}/relationships`, `/relationships/{id}` | Existing, plus `classification`, `claim`, `from_label`, `to_label`, `temporal_context` |
| `GET /api/v1/relationships/{id}/evidence` | **New.** Each support row resolved to its source record |
| `GET /api/v1/cases/{id}/evidence/{kind}/{object_id}` | **New.** `transaction`, `dns_observation`, `hosting_observation`, or `gateway_record`, only inside the case |
| `GET /api/v1/cases/{id}/graph` | Existing, plus `support`, `classification`, `relationship_id`, and `gateway_merchant` edges |
| `POST /api/v1/cases/{id}/correlations`, `/relationships/{id}/confirm`, `/reject` | Existing |

## Response notes

Amounts are four-place strings. Account numbers are masked in lists and
labels. A transaction's evidence includes the narration and the original CSV
row, because it is returned only to someone assigned to the case. A statement
clock has no time zone and is not converted. DNS, hosting, and gateway times
are UTC.

The graph no longer draws `same_payment`. The transfer edge already cites
both statement rows. `same_payment` remains in the relationship list.

## Breaking changes

None for existing fields. New fields were added to graph edges and
relationships. The frontend types were extended, and the correlation and
network pages now show the classification and the support list.
