# Security threat model

This is a design-time threat model for the architecture in
[System architecture](SYSTEM_ARCHITECTURE.md). It is not a penetration test and
not a claim that controls already exist in code. Controls marked Phase 1 are
acceptance criteria for the first implementation. Controls marked Phase 4 must
be in place before official records are stored.

## Assets

| Asset | Why it matters |
| --- | --- |
| Statement bytes and transaction rows | Financial and personal data. |
| Complaint narratives | Allegations and personal data. |
| Infrastructure observations | Can reveal an investigation's focus. |
| Cross-case links | Reveal the existence of other enquiries. |
| Session secrets and password hashes | Account takeover. |
| Audit and evidence rows | The integrity of the case file. |
| Synthetic ground truth | If shown as a finding, it fabricates the investigation. |
| Provider and database credentials | Access to everything else. |

## Actors

| Actor | Position |
| --- | --- |
| Assigned investigator | Legitimate user, can still over-collect or mis-export. |
| Analyst, auditor, administrator | Legitimate, different powers. |
| Unassigned authenticated user | Must learn nothing about the case. |
| Anonymous internet caller | Must learn nothing. |
| Person who can edit a statement before upload | Can poison a case. The system preserves the bytes; it cannot make a forged file true. |
| Person who can place text in a narration | Can attempt prompt injection. |

The product does not have a covert-access mission. "Attacker" here includes
anyone who would turn the tool into a scanner or a way to read cases they are
not assigned.

## Assumptions

- Demo and operational deployments are separate databases and separate data modes.
- TLS terminates in front of the API in any shared deployment.
- Investigators' machines are outside this model's control. Exports can be copied onward. The control is audit and minimisation, not DRM.
- A database superuser can bypass application triggers. Operational hosting must limit that privilege. Until then, the system is not fit for official records.

## Threats and responses

### Spoofing and credential theft

| Threat | Response |
| --- | --- |
| Stolen password | Argon2id hashes. No password in logs or in the repository. |
| Stolen session cookie | `HttpOnly`, `SameSite=Lax`, and `Secure` whenever the request is not loopback HTTP. Loopback HTTP may omit `Secure` only in `synthetic` mode. The server stores the hash of an opaque session id. Logout revokes the row. |
| Session fixation | Login creates a new session id. |

Phase 4 replaces local passwords with the organisation's identity provider. Case
authorisation stays in VAGEXA.

### Authorisation failure

| Threat | Response |
| --- | --- |
| Changing a case UUID in the URL | Repository queries include assignment. Tests cover an unassigned user for every case route. |
| Analyst confirms a link | Role check on the decision endpoint. |
| Cross-case narrative leak | Count and masked identifier only, unless assigned. Audited. |
| Auditor edits a case | Role cannot call mutating use cases. |

Identifier-based object access without the case check is the defect most likely
to ship. It is a release-blocking test, not a best practice note.

### Tampering

| Threat | Response |
| --- | --- |
| Update a transaction to fit a theory | Insert-only trigger. Correction is a new evidence row. |
| Delete an audit event | Insert-only trigger. |
| Change relationship facts while "just" confirming | Trigger allows only status, decider, and time. |
| Upload a different file over the same id | New file, new hash. The old hash remains. |

### Information disclosure

| Threat | Response |
| --- | --- |
| Account numbers in logs | Log statement ids and a last-four suffix. Review tests fail if a logger receives narration. |
| Secrets in git | `.gitignore` blocks `.env` and keys. No default secret in source. |
| Error bodies echo SQL or paths | Problem responses are generic. Detail stays on the server without source data. |
| CSV export becomes a formula when opened | Prefix cells that start with `=`, `+`, `-`, or `@`. |
| Browser bundle contains the database URL or model key | Those values are read only in the API and worker processes. |
| Ground truth served by the API | No route returns `ground_truth`. The application role is not granted a table of answers. |
| Narration rendered as HTML | Reports and previews escape every interpolated value. Narration is not markup. |
| Uploaded filename used as a path | The storage key is server-generated. The original filename is metadata. |

### Repudiation

| Threat | Response |
| --- | --- |
| "I did not run that trace" | `trace.run` audit event with actor and input hash. |
| "The report appeared later" | Report hash stored at export. |

Clock skew is a residual risk. Times are server `timestamptz`, not the browser clock.

### Denial of service

| Threat | Response |
| --- | --- |
| Unbounded graph traversal | Hop cap of 5, default 3. |
| Huge upload | Explicit byte limit on the upload endpoint. The first limit is 25 MB, configurable, rejected before storage grows without a ceiling. |
| Job flood | Worker claims a fixed batch. The API does not parse in the request thread. |
| Passive lookup flood | Adapter off by default and rate-limited. Names must already be on the case. |

### Prompt injection and fabricated intelligence

| Threat | Response |
| --- | --- |
| Narration says to ignore rules and accuse an account | Tools ignore free text as instructions. No tool marks guilt. |
| Model cites an evidence id it was not given | Citation check drops the claim. |
| Model invents an amount | The amount is not in the bundle, so the statement fails the check. |
| Operator presents synthetic output as a real case | Data mode and banner. Mixed classification is rejected. |

### Abuse of the product's reach

| Threat | Response |
| --- | --- |
| Using the worker to scan hosts | No scan capability is designed. `adapters/passive_intel` accepts stored names only. |
| Using exports as a bulk data dump of every case | Exports are per case, authorised, and audited. There is no cross-case export in Phase 1. |

## Logging standard

Structured JSON logs. Required fields: time, level, request id, event name.
Allowed identifiers: case id, statement id, job id, user id, last four
characters of an account number.
Forbidden: password, session token, database URL, narration, complaint text,
full account number, VPA, copilot question, authorization header.

## Security testing that blocks a Phase 1 demo to an external audience

- Unassigned user receives 404 or 403 on case reads without the case title in the body. Use one behaviour consistently: 404, so existence is not confirmed.
- Analyst receives 403 on relationship confirm.
- Append-only trigger test: an attempted update of `transactions` fails.
- Log snapshot test on a parse fixture: the log line does not contain the fixture's full account number.
- Copilot injection fixture does not create a relationship.

## Residual risks

- A person with database superuser or disk access can alter history. Mitigate before operational data, not before a synthetic demo, by role separation and backup integrity.
- The first demo uses one database login. Triggers still apply. The gap is documented in the roadmap.
- Client machines can leak exports. That is an organisational control.
- Passive DNS still reveals queries to the resolver operator. Leave it off when the demonstration does not need live lookups.
- This document will go stale. Revisit it when the first implementation exists and again before any official record is ingested.
