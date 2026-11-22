# Phase 1 scope

Date: 2026-11-22. This file freezes a build order after the architecture
audit. It does not start the build. Phase 1 in the roadmap is still the
hackathon milestone plus the foundation. This note splits that phase into what
is specified tightly enough to code, what is blocked, and what is out of scope
even if an earlier sentence called it P1.

The public problem statement this scope serves is the money-trail paragraph
cited in [Architecture audit](ARCHITECTURE_AUDIT.md). It is not a claim that a
full official PS05 brief was available.

## Decided for this phase

| Item | Decision |
| --- | --- |
| Fan-in and fan-out | Count verified edges only. Say when narration links were excluded. |
| Horizon | 3. The four-hop synthetic chain leaves the last beneficiary as `outside_horizon`. The screen uses that word. |
| Fixture | The synthetic tables in the data validation report. |
| Administrator | Case content requires assignment, including for an administrator. |
| Copilot | The client sends a tool name. Optional text is stored and is not a router. |

## Increment 1A — skeleton

In scope:

- Package layout from the architecture document.
- Compose: Postgres, API, worker, web. Postgres unpublished.
- Migration for identity, cases, assignments, sessions, instruments,
  observations, source files, statements, transactions, provenance, evidence,
  audit, jobs, and the append-only triggers named in the database design.
- The corrected shapes: immutable instrument keys, append-only account
  observations, required subject account before a statement is accepted,
  `exit_kind` on trace flows, `supersedes_statement_id`, relationship
  `case_id` not null, server-generated storage keys.
- Login, logout, me. Opaque session id, hash stored. Cookie rules from the
  threat model, including the loopback exception.
- Create and read a case. Assignment check. 404 when not assigned.
- Health endpoints.
- Tests: unassigned user, trigger rejects a transaction update, synthetic mode
  rejects `official`.

Out of this increment: FIFO, indicators, graph drawing, copilot, live DNS.

## Increment 1B — investigation slice

In scope after 1A is green:

- Canonical CSV ingest with the subject account required.
- Reprocess as a new statement row, not an update.
- `fifo.v1` with the sort order and the per-account conservation check.
- Residuals, including `outside_horizon` and `no_onward_record`.
- Indicators `FAN_IN`, `FAN_OUT`, and `PASS_THROUGH` under the decided edge set, with dwell skipped when times are missing.
- Case graph of statement-backed edges plus FIFO edges, assertion kinds distinct, hop cap 5, default 3.
- Manual domain and IP observations. Overlap claim limited as ADR 0011.
- Computed cross-case signal. No foreign narrative.
- HTML report, escaped, with limitations and the non-guilt sentence.
- Direct copilot tools: `summarize_case`, `trace_summary`, `list_indicators`, `common_beneficiaries`, `infrastructure_for_case`, `list_evidence`. The client sends the tool name. No model.
- The synthetic tables in the data validation report are the fixture, per ADR 0014. They are labelled synthetic. Horizon 3 leaves account B as `outside_horizon`.

## Explicitly not in Phase 1

- PDF parsing, pro-rata, community detection, centrality, cycle labels.
- Live DNS in the demo. A fake resolver may exist in tests.
- RDAP, certificate transparency, ASN lookups.
- An LLM provider, a vector database, Neo4j, Redis.
- OIDC, disk encryption, and operational retention. Those are Phase 4.
- Scraping any portal, and any dataset that is not marked synthetic.
- A Boolean or score that means mule, guilty, or owner.

## Demo script the slice has to support

An assigned investigator, on synthetic data:

1. Signs in and cannot open an unassigned case.
2. Opens a case whose banner says synthetic.
3. Sees transactions that point at a file hash and a line.
4. Sees a three-hop attributed path and a visible residual where the statements or the horizon stop.
5. Sees fan-in and fan-out with the transactions that counted, and sees the threshold.
6. Sees two domains and one IP with the non-ownership limitation on screen.
7. Sees a second printed holder name on the same instrument without one of them disappearing.
8. Sees a shared account in another case only as a masked count.
9. Runs a tool action and gets evidence ids with no model configured.
10. Exports a report that still reads if the model setting is `none`.

Step 4 must not be described as finding the final beneficiary if the run used
horizon 3 and the beneficiary sits in the residual. That wording is an audit
failure even if the code is fast.

## Acceptance

1A is accepted when the migration matches the corrected database design, the
three tests in 1A pass, and no analytical module has been started by stealth.

1B is accepted when the ten demo steps above are true on a clean Compose
stack and the conservation test uses a multi-hop fixture whose hop sum is
greater than the seed. A test that only traces one hop does not accept C01.

## Cut order if the milestone is short

Cut in this order: live DNS, report visual polish, extra indicator codes.
Free-text routing is already out of this phase. Do not cut assignment checks,
the subject-account rejection, residuals, assertion kinds, the overlap
limitation, or the synthetic banner.
