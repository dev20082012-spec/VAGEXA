# Architecture audit

Date: 2026-11-22. Scope: the documentation, decision records, Cursor rules, and
repository layout as they stood before this audit. No application code exists.
This review does not treat the previous design as correct because it was
written down.

Findings are identified even where this audit also corrects a document. A
correction is marked in the disposition column and in the edited document.
Open rows are not resolved here.

## How this was reviewed

Every file under `docs/`, `docs/decisions/`, and `.cursor/rules/` was read, as
were `README.md`, `LICENSE`, `NOTICE`, `CONTRIBUTING.md`, and `.gitignore`.
The repository has no application, migration, or Compose file. Claims below
are about that text, not about a running system.

## PS05

The repository never uses the identifier PS05. The public hackathon page lists
five problem statements and, in the text available to this review, does not
number them and does not publish the feature list or sample-file schema that
the page says each brief contains.

Assumption, labelled as such: PS05 means the fifth public statement,
**Financial Crime Infrastructure & Money-Trail Analysis System**. The only
public requirement this review can rely on is that paragraph: analyse bank
statements, trace suspected mule-account movement, examine domains, IP
addresses, and hosting, and show links between cases. If the team holds a
longer official brief, it is not in this repository and this audit does not
invent it.

Against that paragraph, the intended product is the right product. The design
is not yet a reliable design for it. A three-hop chain cannot pass the written
conservation check. A statement file does not identify the account that booked
the rows. Shared hosting can be stored as an inference that reads like common
control. Those are implementation blockers, not polish.

## What should be kept

These choices survive the review:

- PostgreSQL as the only system of record, with NetworkX for a bounded
  case graph. The expected queries are exact-key matches and short paths, not
  corpus-wide community detection. A second database is not justified.
- One Python package for the API and the worker. Two processes, one database.
  Not a microservice estate.
- Assertion kind separated from workflow status. Confirmation must not launder
  a hypothesis into a source fact.
- No guilt flag, no culpability score, and no model that writes entities.
- Synthetic and operational deployments on separate databases.
- Append-only triggers on source transactions, evidence, and audit.
- Passive infrastructure collection, with scanning excluded.

## Finding register

| ID | Area | Existing design | Identified problem | Severity | Recommended correction | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| C01 | Financial | Sum of all attributed flows for a complaint must be within 0.01 of the seed. | A 100 onward through three hops emits flows of 100 three times. The sum is 300. Every real multi-hop trace fails. | Critical | Conserve value per account: attributed outflow cannot exceed attributed inflow at that account. Do not sum hops and compare the total with the seed. | Corrected in the financial docs and ADR 0010 |
| C02 | Financial | Canonical CSV has counterparty columns. The statement subject account is optional and must not be guessed. | Debit and credit have no owner. FIFO and layers cannot start. | Critical | Reject a parse unless the upload names the subject account number and IFSC, or the subject VPA. | Corrected in the financial and database docs and ADR 0012 |
| C03 | Data model | One global `accounts` row holds a single holder name, bank name, and classification, and is not append-only. | Two sources cannot disagree. A synthetic row and an official row cannot share a key even in separate discussions of the schema. Updating the holder rewrites history. | Critical | `accounts` is an immutable instrument key. Names and printed numbers live in append-only `account_observations` scoped to a case and a provenance record. Synthetic and official data stay in separate databases. | Corrected in the database design and ADR 0013 |
| C04 | Financial | Cash exit described as `from_account_id` null, and `trace_flows` has no rail or exit column. | A withdrawal's source is the account. The null was on the wrong side, and the column the sentence refers to does not exist. | Critical | `from_account_id` is required. `to_account_id` is null only with `exit_kind` set, including `cash`. | Corrected in the database design |
| C05 | Infrastructure | Shared IP or hosting across cases is `shared_infrastructure`, assertion `inferred`. | Shared hosting and shared DNS do not support common ownership or common control. `inferred` is the wrong claim. | Critical | Store an overlap: the same key was observed. Assertion `verified` for that co-occurrence only, with a mandatory limitation that control and ownership are not established. Do not create a party. | Corrected in the correlation and infrastructure docs and ADR 0011 |
| C06 | Security | `GET /accounts/{id}` and `POST /relationships/{id}/confirm` are authorised by a loose "assigned investigator" phrase. `relationships.case_id` may be null. | A global id is an object-level authorisation bypass. A null case has no assignment check. | Critical | Confirm and reject resolve `case_id` and require assignment. Stored relationships require `case_id`. Cross-case results are computed queries, not global rows. Account read requires assignment to a case that cites that instrument. | Corrected in the API and database docs |
| C07 | Evidence | Same file hash returns the old statement and does not reparse. Supersession sits on `evidence_records`. Traces read `transactions` directly. Transaction tables are insert-only, so a bad parse cannot be replaced in the queries that matter. | A parser defect is permanent, or a second insert double-counts, depending on which sentence an implementer follows. | Critical | One stored blob per hash. A reprocess inserts a new statement that points at the previous statement. Analytical queries read transactions of statements that have no newer reprocess. | Corrected in the evidence, API, and database docs and ADR 0012 |
| C08 | Financial | FIFO "may" net reversals. Same-day rows have no sort key. `booking_time` may be null. | `FR-EVD-05` requires the same amounts on a rerun. The written policy does not have a total order. | Critical | Sort by booking date, booking time with nulls last, line number, then transaction id. Net a reversal only when the reference, currency, and amount rule match. Date-only order is file order and must be stated on the run. | Corrected in the financial docs and ADR 0010 |
| H01 | Financial / graph | Fan-in and fan-out count verified transfer edges. The graph load list is trace flows, complaints, and observations. | Narration-only counterparties are `inferred`, so they never count. Statement-backed links are invisible until a trace exists. The trace is what the investigator needed the graph for. | High | The graph always includes statement-backed counterparty edges. `FAN_IN` and `FAN_OUT` count verified edges only, and the indicator says narration-only links were excluded. | Decided by the owner. ADR 0014 |
| H02 | Correlation | `FR-COR-02` calls a domain string in a narrative a hypothesis. The correlation catalogue calls an exact host in stored text `verified`. | Implementers can follow either document. | High | Exact containment of a host in stored text is `verified` for the claim "the text contains this host" and for no broader claim. | Corrected in the requirements. ADR 0006 already required this meaning |
| H03 | Testing | `ring-01` says three complaints, then talks about three cases. No amounts, times, or pass-through ratio are fixed. Default horizon is 3. | The acceptance test cannot be built. A victim plus three intermediaries plus a final beneficiary is four hops. Horizon 3 stops on the third intermediary and leaves the beneficiary as `outside_horizon`. | High | Keep horizon 3. The demo shows the residual and does not call that residual the final beneficiary. The synthetic tables in the data validation report are the fixture. | Decided by the owner. ADR 0014 |
| H04 | Security | `FR-ACC-03` lets an administrator read case data. The vision says the administrator does not get case narratives beyond the audit need. Global role and case role are both defined and neither wins. | An implementer will pick the more convenient reading. | High | A global administrator reads a case only when assigned to it. Assignment is the gate for narratives and financial rows. Global powers are user and assignment management. | Decided by the owner. ADR 0014 |
| H05 | Copilot | System architecture stores the question "on the case audit". Audit detail must not contain the question. | The question would land in the table that forbids it, or the audit row would be incomplete. | High | Persist the question only on `copilot_queries`. Audit detail keeps mode, tool names, and the bundle hash. | Corrected in the architecture doc |
| H06 | Evidence | Confirming a relationship "does not upgrade a hypothesis unless a source field states the claim." Correlation says confirmation does not change assertion kind. | Status and kind get mixed at the moment a person clicks confirm. | High | Status changes. Kind does not. If a source field states the claim, the row is created as `verified`. | Corrected in the architecture doc |
| H07 | Security | The report is HTML and includes narrations and complaint text. | Those strings are untrusted. Unescaped HTML is stored script in an investigator session. | High | Escape every interpolated value. Do not interpret narration as markup. | Corrected in the threat model |
| H08 | Security | The session cookie is always `Secure`. The demo is HTTP on one published port. | Login cannot set the cookie on the deployment the roadmap calls the demo. | High | `Secure` stays on whenever traffic is not loopback HTTP. Loopback HTTP is allowed only in `synthetic` mode, via an explicit setting. | Corrected in the threat model and the security rule |
| H09 | Security | `storage_key` is unspecified. `original_filename` is stored. | Using the client filename as a path allows traversal and collisions. | High | The server generates the storage key. The original filename is display metadata and is never a path segment. | Corrected in the database design |
| H10 | Financial | Pass-through dwell default is 24 hours. Many rows have date precision only. | Treating a missing time as midnight invents a clock time the evidence rules forbid. | High | If either side lacks a time, do not apply the dwell test. The limitation must say dwell was not tested. | Corrected in the financial docs |
| H11 | Copilot | Phase 1 accepts arbitrary questions and routes on keywords such as "trace" and "domain". | Keyword routing is brittle, and a language model is the wrong tool for allocation, counts, and identifier matches. The public PS05 paragraph does not require a chatbot. | High | Phase 1 calls a named tool directly. Optional free text is stored and does not select the tool. | Decided by the owner. ADR 0014 |
| M01 | Financial | Cycles are not mentioned. The hop cap stops a walk. | A return to an earlier account is visible only if someone notices two edges. There is no `CYCLE` result, and there should not be a model that labels it laundering. | Medium | A later deterministic finder may report "path revisited an account", with the flow ids. Do not add it to the milestone. | Deferred |
| M02 | Data model | `from_kind` plus `from_id` has no foreign key. | The database cannot reject an edge to a missing account. | Medium | Application checks on write. Typed tables are a later option if orphans appear in tests. | Deferred |
| M03 | Evidence | `source_files.status` and `jobs.status` are updated in place. | Parse and job history can be overwritten without a new row. | Medium | Audit the status transition. Do not extend in-place update to transactions or observations. | Deferred |
| M04 | Evidence | Confirm, reject, and resolution decisions exist. A general analyst note does not. | An investigator cannot attach a sourced comment to an account without pretending it is a relationship. | Medium | Add append-only annotations when the case screen is built, not before the schema for instruments is stable. | Deferred |
| M05 | Infrastructure | Phase 3 says RDAP and certificates use the same observation model. The schema has DNS and hosting rows, not certificate rows. | The phase text is ahead of the tables. | Medium | Add a certificate observation table in the phase that ingests certificates. Do not pretend `dns_observations` can hold them. | Deferred |
| M06 | Requirements | Traces finish within 10 seconds on "a developer laptop". | That target cannot be failed in CI. | Medium | Measure the adopted synthetic fixture in CI against the Compose PostgreSQL. | Deferred to the first CI run |
| M07 | Documentation | README says four classifications and lists five. | Readers will mis-count the enum. | Medium | Say five. | Corrected in the README |
| M08 | API | `POST /traces` returns a job. `GET /traces/{trace_id}` returns a run. The link is unspecified. | The client cannot find the run from the job it was given. | Medium | Create the analytical run and the job in one transaction. The job payload stores the run id. | Corrected in the API spec |
| M09 | Infrastructure | A domain is one normalised string. | `a.syn.example` and `syn.example` do not meet. Parent-domain grouping is unsupported. | Medium | Leave it out of Phase 1. A later hypothesis may group by registrable domain and must still not claim common ownership. | Deferred |
| M10 | Financial | Running balance is stored and not checked. | An internally impossible statement is ingested as quietly as a sound one. | Medium | A data-quality finding may report broken balance continuity. It is not an offence indicator. | Deferred |
| M11 | Security | Cookie is `SameSite=Lax`. Configuration text says the session secret signs the cookie. The session row stores a token hash. | Lax blocks cross-site POST from other sites. It is not a CSRF token. Signing and opaque tokens are two designs. | Medium | Use an opaque random session id, store only its hash, and keep Lax. Add a CSRF token before any non-browser client shares the cookie. | Open as a refinement, opaque token preferred |
| M12 | Correlation | API example: "Two complaints share the account." | A shared printed number is not a shared owner. | Medium | Template text says the normalised identifier co-occurs and cites the rows. | Corrected in the API example |
| L01 | Data model | Account kind includes `wallet` with no key defined. | A wallet row cannot be matched or distinguished. | Low | Do not emit `wallet` until a key scheme exists. | Deferred |
| L02 | Data model | `complaints.external_reference` is not unique per case. | The same complaint can be loaded twice. | Low | Unique `(case_id, external_reference)` where the reference is present. | Deferred |
| L03 | Security | Argon2id is required. Memory, time, and parallelism are not. | Implementations will pick convenient weak parameters. | Low | Set the parameters in the first auth implementation and test them. Do not invent a second password scheme. | Deferred to 1A |
| L04 | Graph | ADR 0004 is conditional on a measurement. No case size is written down. | "Too slow" has no denominator. | Low | Planning assumption: a case holds up to a few thousand transactions; cross-case work is an equality lookup, not a graph walk. Revisit the assumption when a real corpus exists. | Recorded as an assumption in the technology note |

Counts: 8 critical, 11 high, 12 medium, 4 low.

## Deterministic methods and methods that do not belong yet

Reliable from the records alone, with a versioned rule and a visible gap:

- Normalisation of an account number, IFSC, VPA, domain, and IP.
- A transfer the statement's own counterparty field names.
- A join of two legs on an equal structured reference.
- FIFO or pro-rata allocation inside a horizon, once the total order is fixed.
- Fan-in and fan-out counts on a declared edge set and window.
- A pass-through ratio when both inflow and outflow are in the supplied statements.
- Exact co-occurrence of an identifier across cases.
- Co-occurrence of an IP, nameserver, or provider string, reported as overlap.
- A cycle or a return to an earlier account, as a graph fact, when someone writes that finder.
- Repeated amounts near a configured threshold. The threshold is a parameter, not a statute. This product does not contain a legal structuring threshold, and this audit does not invent one.

Not reliable, and not a Phase 1 or Phase 2 model:

- Beneficial ownership, guilt, or "mule" as a class label.
- Common control from shared hosting, shared DNS, or a shared IP.
- A score trained on "normal customers". This system has no population baseline.
- Filling a missing hop because similar cases continued that way.
- Choosing among two holder names because one is more common.

Statistical or learned methods become discussable only after a defined baseline, a labelled synthetic set that is not the training set, and a report that shows the feature values. They are not required for the public problem statement this review can see.

## Investigation workflows that are still incomplete

The happy path is specified: upload, seed, trace, indicate, draw, confirm, ask, export.

These workflows are not specified as investigator procedures:

- What the analyst does when the subject account is missing, other than receive a rejection.
- How a contradiction between two holder names is closed. The corrected model can store both. It does not say who may leave them unresolved. Unresolved should be the default.
- How a horizon residual is acted on. Rerun with a higher horizon is the only honest action, up to 5.
- How an analyst records "I looked and I do not accept this overlap" without a relationship row. That is the missing annotation (M04).

## Decisions closed by the owner

On 2026-11-22 the owner selected the following. ADR 0014 records them.

| Topic | Decision |
| --- | --- |
| `FAN_IN` and `FAN_OUT` | Verified statement fields only. Narration links remain on the graph and do not count. |
| Horizon and the demo chain | Horizon stays 3. A longer chain is shown with `outside_horizon`. That residual is not labelled as the final beneficiary. |
| Administrator narratives | No case read unless that administrator is assigned to the case. |
| Copilot invocation | Named tools only in Phase 1. Free text may be stored. It does not start a trace. |

## Assumptions

- PS05 is the fifth public problem statement, as qualified above.
- A demonstration case contains at most a few thousand transactions. Cross-case search is equality on normalised keys.
- Organiser sample files are unavailable. The canonical CSV plus a required subject account is the contract until a sample arrives.
- No official records are loaded for the hackathon.
- The copyright owner remains `[COPYRIGHT OWNER TO BE CONFIRMED]`.

## Implementation readiness

The architecture is ready for increment 1A, the skeleton and the corrected
schema. It is not production-ready, and it is not a finished investigation
product. Increment 1B can follow 1A using ADR 0010 through ADR 0014. A
migration encoded from the pre-audit account table would have to be thrown
away. Medium and low findings stay deferred and do not block 1A.
