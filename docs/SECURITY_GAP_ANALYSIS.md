# Security gap analysis

Date: 2026-11-22. This is a gap analysis of the written design. It is not a
penetration test, and it is not evidence that any control exists in code.
Nothing in the repository is production-ready.

The threat model remains useful. This document separates the minimum bar for a
synthetic hackathon prototype from the bar before any official record is
stored, and it records holes the threat model missed.

## Minimum controls for a synthetic prototype

These are required before an external person uses the demo, including a jury
machine. They are design obligations, not implemented controls.

| Control | Why it is in the prototype | Status in the design |
| --- | --- | --- |
| Local accounts, Argon2id, server-side session, token stored only as a hash | Stops anonymous reads of the demo cases | Specified. Cost parameters are not (L03). |
| Case assignment checked on every case route, 404 when absent | Stops a logged-in user reading another team's case | Specified, and now also required for account reads and relationship decisions (C06). |
| `synthetic` data mode, banner, refusal of `official` | Stops a demo being mistaken for a real case file | Specified. |
| Append-only triggers on transactions, evidence, and audit | Stops a casual update from rewriting a parse | Specified. |
| Upload size limit, hop cap, parser errors that insert no rows | Bounds abuse of the worker | Specified. |
| Redacted logs | Stops account numbers in container logs | Specified. Test is specified and not written. |
| Server-generated storage keys | Stops path traversal via the uploaded filename | Added after H09. |
| Escaped HTML report | Stops narration from running as script | Added after H07. |
| Postgres not published to the host | Stops the database being the demo's front door | Specified in the deployment doc. |
| Cookie `Secure` on any non-loopback deployment | Stops the session travelling in clear text on a shared network | Clarified after H08. Loopback HTTP is the only exception, and only in synthetic mode. |
| No ground-truth route | Stops the answer key becoming a finding | Specified. |
| Passive intel off unless configured | Stops the demo querying arbitrary names | Specified. |

A prototype that skips assignment checks, stores session tokens in the
browser's local storage, or renders narration as HTML has not met this bar.
Missing Neo4j, OIDC, or a metrics stack has not, by itself, missed it.

## Additional controls before official records

Do not load operational data until all of the following exist:

| Control | Gap today |
| --- | --- |
| Separate database roles, with the application role unable to update transactions or delete audit rows | Designed, explicitly not enforced in the demo's single login. |
| TLS in front of the web process, `Secure` cookies, and no loopback exception | Demo topology is HTTP. |
| Encryption at rest for the database volume and the statement-byte volume, including backups | Not specified beyond "backup media encrypted" in Phase 4. Disk encryption of the live volume is unnamed. |
| A secret store. No long-lived database password in a Compose file on a shared host | Env file is specified as gitignored. That is not a production secret store. |
| OIDC against the organisation's identity provider, local passwords disabled | Phase 4. |
| Field-level audit when a full account number is revealed | Phase 4. Phase 1 audits case open, not each reveal. |
| Restore rehearsal | Phase 4. |
| A written retention and legal-hold rule | Unresolved. No period is invented here. |
| Administrator narrative access is assignment, not a global bypass | Decided in ADR 0014. Still has to be implemented and tested. |
| Cross-case counts confirmed not to leak titles | Specified. Needs a test. |
| Threat-model review against the code that shipped | The current threat model is design-time only. |

## Gaps found in this audit

| ID | Gap | Prototype impact | Before real data |
| --- | --- | --- | --- |
| C05 | Shared IP stored as an inference of a relationship | High. A demo can teach the wrong conclusion. The copy and the assertion kind are the control. | Same control. A model must not "upgrade" it later. |
| C06 | Object id used as authorisation | Blocking. Fix in the first case routes, not later. | Same. |
| H04 | Administrator narrative access | Decided: assignment is required. The 1A test must show an unassigned administrator receives 404. | Same rule before real data. |
| H07 | HTML injection via narration | Blocking for any shared demo that exports or previews HTML. | Same. |
| H08 | `Secure` cookie on HTTP | Loopback demo can exempt it. A laptop on the venue network cannot. | TLS required. |
| H09 | Filename as a path | Fix in the first upload. | Same. |
| M11 | No CSRF token | Acceptable only for a same-site browser talking to its own origin with `SameSite=Lax`. | Revisit before any cookie is sent cross-site. |
| M03 | Job and file status overwritten | Low for a synthetic demo. | Audit the transitions before they are used as evidence of processing. |
| — | No encryption in transit between API and Postgres | Acceptable on a single-host Compose network that is not shared. | Required on any network that is not the host's private namespace. |
| — | No application-level field encryption | Not required for the synthetic prototype. | Decide with the operational owner. Volume encryption covers theft of the disk and does not cover a stolen application credential. |
| — | Copilot questions stored in full | They can contain pasted account numbers. Access is the case ACL. | Retention must be the case retention, once one exists. Do not ship questions to a model provider in the prototype. |
| — | Single database login | Accepted for synthetic mode only. Triggers still have to exist so the application code is not the only barrier. | Not accepted. |

## Secrets

The repository contains no secrets and no `.env` file. The gitignore covers
`.env`, keys, and storage directories. The design says there is no default
session secret. That rule has no code to violate yet. The first Compose file
must not embed a usable password in a tracked file.

## Authorisation matrix the implementation has to test

| Action | Investigator assigned | Analyst assigned | Auditor assigned | Administrator | Unassigned user |
| --- | --- | --- | --- | --- | --- |
| Read case | Yes | Yes | Yes | Only if assigned | 404 |
| Upload | Yes | No | No | Only if assigned as investigator | 404 |
| Run trace | Yes | Yes | No | Only if assigned as investigator or analyst | 404 |
| Confirm relationship | Yes | No | No | Only if assigned as investigator | 404 |
| Read other case narrative via a shared key | No, count only | No, count only | No, unless assigned | No, count only, unless assigned | 404 |
| Read audit | Yes, own case | Yes, own case | Yes, assigned cases | Only if assigned | 404 |

An administrator manages users and assignments without that work granting a
case read. Demo accounts, including any administrator, are assigned to the
cases they are meant to open.

## What this analysis does not claim

Logging redaction, triggers, and 404 behaviour are specified and unbuilt.
Describing them here does not mean the prototype is safe to receive real bank
statements. Operational deployment remains Phase 4, and only after the open
access decision.
