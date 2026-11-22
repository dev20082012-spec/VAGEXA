# Product requirements

Requirements are numbered so later changes can cite them. Priority `P1` is the
hackathon milestone and the first production-shaped slice. Later priorities
belong to the phases in [Implementation roadmap](IMPLEMENTATION_ROADMAP.md).

The public R4C brief asks for bank-statement analysis, mule-account tracing,
domain and hosting intelligence, correlation, and links between cases. Where
that brief does not publish a file format or a legal rule, this document says
so and specifies an adapter instead of inventing a format.

## Personas and access

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-ACC-01 | A user signs in with a local account. The session is server-side. | P1 |
| FR-ACC-02 | Roles are administrator, investigator, analyst, and auditor. | P1 |
| FR-ACC-03 | Case narratives, statements, and transactions are visible only to a user assigned to that case. A global administrator who is not assigned receives 404. Administrator duties that remain global are user management and assignment. | P1 |
| FR-ACC-04 | An analyst may run traces and read results. An analyst may not confirm or reject a relationship. | P1 |
| FR-ACC-05 | An auditor assigned to a case may read that case and its audit trail and may not change them. | P1 |
| FR-ACC-06 | Authentication can later move to an external identity provider without rewriting case authorisation. | P4 |

## Cases and complaints

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-CASE-01 | An investigator creates a case with a reference, a title, a status, and a data classification. | P1 |
| FR-CASE-02 | A case is entirely `synthetic` or entirely non-synthetic. Mixed cases are rejected. | P1 |
| FR-CASE-03 | A complaint stores an external reference, a report time when known, a narrative, and provenance. | P1 |
| FR-CASE-04 | The investigator marks confirmed seed transactions for a trace. The system does not start a trace from a fuzzy match. | P1 |
| FR-CASE-05 | Closing a case blocks new ingestion and new confirms. Existing records stay readable. | P2 |

## Financial intelligence

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-FIN-01 | The investigator uploads a statement file. The original bytes are stored and hashed before parsing. | P1 |
| FR-FIN-02 | A CSV parser maps columns into the canonical transaction. PDF parsing uses the same canonical model later. | P1 CSV, P2 PDF |
| FR-FIN-03 | Re-uploading the same bytes for the same case does not duplicate transactions. | P1 |
| FR-FIN-04 | Each transaction keeps statement id, line number, direction, positive amount, currency, dates, rail, raw narration, and raw counterparty text. | P1 |
| FR-FIN-05 | Date-only values stay dates. Missing times are not filled with midnight. | P1 |
| FR-FIN-06 | VPA and UTR extraction is versioned. Unmatched narrations stay unresolved. | P1 |
| FR-FIN-07 | A trace run records policy name, version, parameters, seeds, and actor. | P1 |
| FR-FIN-08 | The default policy attributes value with FIFO, to a maximum of 3 hops, hard cap 5. | P1 |
| FR-FIN-09 | The run emits layer-1, layer-2, and layer-3 flows and an explicit residual of untraced value. | P1 |
| FR-FIN-10 | Fan-in and fan-out are counts of distinct counterparties on verified transfer edges in a stated window. | P1 |
| FR-FIN-11 | Pass-through, fan-in, and fan-out indicators include support ids, thresholds, and method version. | P1 |
| FR-FIN-12 | The system refuses to store a Boolean guilt or mule flag. | P1 |
| FR-FIN-13 | A second allocation policy (pro-rata) can be selected explicitly. | P2 |
| FR-FIN-14 | Additional anomaly rules (structuring, night-time bursts, round amounts) are versioned indicators. | P2 |

## Graph intelligence

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-GRAPH-01 | A case graph endpoint returns nodes and edges for a focus and a hop bound. | P1 |
| FR-GRAPH-02 | Edges include assertion kind, method, amount as a decimal string, and evidence ids. | P1 |
| FR-GRAPH-03 | The response says whether the bound truncated the graph. | P1 |
| FR-GRAPH-04 | Connected components are available inside the loaded subgraph. | P1 |
| FR-GRAPH-05 | Community detection, if added, is labelled as an inference and stored with its algorithm version. | P2 |
| FR-GRAPH-06 | Entity resolution suggestions from weak signals are hypotheses. A merge requires an investigator decision and does not delete accounts. | P2 |

## Digital infrastructure

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-DIG-01 | An investigator can record a domain, IP, or hosting note against a case, with provenance. | P1 |
| FR-DIG-02 | A passive DNS lookup for an investigator-supplied name stores the observation time, resolver, and record. It does not overwrite older observations. | P1 |
| FR-DIG-03 | RDAP, certificate-transparency, and ASN lookups are further adapters on the same observation model. | P3 |
| FR-DIG-04 | The product does not scan ports, exploit services, or collect data the investigator did not identify. | P1 |

## Correlation

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-COR-01 | An exact shared account number plus IFSC, or an exact VPA, across two complaints produces an inferred cross-case signal. | P1 |
| FR-COR-02 | An exact host string contained in stored complaint or narration text is `mentioned_in` with assertion `verified` for containment only. Confirmation does not widen that claim into use or ownership. | P1 |
| FR-COR-03 | Confirm and reject are explicit actions with an actor and a time. Rejected links stay stored. | P1 |
| FR-COR-04 | A user who cannot open the other case sees the identifier and a count, not the other narrative. | P1 |
| FR-COR-05 | Name similarity never confirms a link by itself. | P1 |

## Copilot

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-AI-01 | The investigator runs a named copilot tool inside a case. Optional free text is stored with the query and does not select the tool. | P1 |
| FR-AI-02 | With no model configured, the system still answers from a fixed tool list in a structured form. | P1 |
| FR-AI-03 | Assisted mode sends only the tool results and the question to a model, then drops claims that cite unknown evidence ids. | P2 |
| FR-AI-04 | Each query stores the actor, mode, tool trace, evidence-bundle hash, and response. The question is stored on the case, not in application logs. | P1 |

## Evidence and reporting

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-EVD-01 | Every source file, normalised row, observation, trace, and finding has provenance. | P1 |
| FR-EVD-02 | Evidence, provenance, analytical runs, findings, and audit events are append-only. | P1 |
| FR-EVD-03 | A correction inserts a new record that cites the record it supersedes. | P1 |
| FR-EVD-04 | An HTML report includes classification, method versions, findings, evidence ids, gaps, and a limitation statement. | P1 |
| FR-EVD-05 | Re-running the same policy on the same seeds and inputs yields the same flow amounts. | P1 |

## Non-functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-01 | Once `ring-01` is fully specified, its trace completes within 10 seconds in CI against the Compose PostgreSQL. "A developer laptop" is not the acceptance target. | P1 |
| NFR-02 | Graph requests refuse hop counts above 5. | P1 |
| NFR-03 | Logs contain request ids and redacted identifiers only. | P1 |
| NFR-04 | A health check reports process liveness and database readiness separately. | P1 |
| NFR-05 | A demo deployment can be started with Docker Compose and contains no official records. | P1 |
| NFR-06 | Dependencies stay limited to the set recorded in the architecture decision records. | P1 |
| NFR-07 | Backups and restore are rehearsed before any operational data is stored. | P4 |

## Out of scope

- Payment blocking, lien marking, and core-banking integration.
- Unofficial access to NCRP, banks, or registrars.
- CDR, IPDR, CCTV, APK, and social-media collection.
- Automatic legal conclusions or charge recommendations.

## Milestone acceptance

The hackathon slice is accepted when an assigned investigator can:

1. sign in and open only assigned cases;
2. load the synthetic scenario described in [Testing strategy](TESTING_STRATEGY.md);
3. see normalised transactions that point back to file hash and line number;
4. run the FIFO policy and inspect layers 1 to 3, including a split and a merge;
5. see fan-in, fan-out, and pass-through indicators with support rows;
6. open a graph that keeps assertion kinds distinct;
7. see one shared beneficiary across two complaints and one domain observation;
8. ask a copilot question and receive an answer that cites those records without a model configured;
9. export a report that still reads correctly if the model is absent;
10. find an audit event for the upload, the trace, and the export.

Sample files from the organiser, if they differ from the canonical CSV, are
handled by a new parser adapter. They are not a reason to fork the transaction
model.
