# Implementation roadmap

The phases are a sequence of dependable increments. Phase 1 includes the
hackathon milestone. Later phases assume the evidence model and the canonical
transaction stay stable. A phase is not a licence to rewrite the system of
record.

Nothing in this roadmap has been implemented. The documentation in `docs/` is
the Phase 1 deliverable that this repository now contains.

External date check: public pages for the Rajasthan Police Hackathon 2026 have
not agreed with each other on the registration cut-off. The official site
consulted while writing this roadmap described registration through 22 November
2026 and an action-plan submission, with a 24-hour final at the Rajasthan
Police Academy, Jaipur, on 28–29 November 2026. Confirm those dates on
[rajasthanpolicehackathon.in](https://rajasthanpolicehackathon.in/) before
planning a submission around them.

## Phase 1 — Foundation and hackathon milestone

### Functional objectives

- An assigned investigator can sign in, create a synthetic case, and load
  scenario `ring-01`.
- Canonical transactions preserve source line and file hash.
- FIFO `fifo.v1` produces layers 1 to 3, including the planted split, merge,
  and residual.
- Indicators `FAN_IN`, `FAN_OUT`, and `PASS_THROUGH` cite support rows.
- The case graph keeps assertion kinds distinct.
- A shared account is visible across the fixture complaints, with the
  cross-case access rule enforced.
- A domain observation is stored and shown.
- The copilot answers from tools with no model configured.
- An HTML report includes methods, gaps, and the non-guilt limitation.
- Audit events exist for upload, trace, and export.

Increment 1A is the skeleton: package layout, compose, migration, auth,
append-only triggers, health. Increment 1B is the vertical slice above. Do not
start 1B by skipping the triggers and the authorisation tests.

### Technical dependencies

- Accepted ADRs 0001 through 0009.
- PostgreSQL 16, Python 3.12, Node only as the frontend build tool.
- Docker for the demo topology.
- No organiser sample file is required to start. The canonical CSV is the
  contract. A sample that arrives later is a new parser.

### Deliverables

- Repository skeleton matching [System architecture](SYSTEM_ARCHITECTURE.md).
- Alembic migration for the tables and triggers in [Database design](DATABASE_DESIGN.md).
- `ring-01` generator and fixtures.
- API routes in [API specification](API_SPECIFICATION.md) for the objectives above.
- React workspace: sign-in, case, transactions, graph, observations, copilot, report download.
- Compose file and a short operator note in the README once the commands are real.
- Automated tests listed in [Testing strategy](TESTING_STRATEGY.md).

### Acceptance criteria

The ten checks in the milestone section of [Product requirements](PRODUCT_REQUIREMENTS.md) pass on a clean compose stack in `synthetic` mode. An unassigned user cannot read the case. A transaction update through the application role fails. The provider setting `none` still yields a copilot answer.

### Testing requirements

Domain tests for FIFO and conservation, repository tests for triggers and
classification, HTTP tests for authorisation and the copilot fallback, and the
`ring-01` journey. Frontend tests for the banner, assertion labels, and case
switching once those screens exist, plus a manual pass through the running UI.

### Known risks

- The public event calendar needs confirmation, and the milestone is larger
  than a single evening. If time is short, cut PDF, live DNS, and assisted
  narration. Do not cut provenance, the hop cap, or authorisation.
- The organiser's file layout may differ from the canonical CSV.
- A graph that is visually dense can be mistaken for an accusation. The report
  text and the legend are part of the milestone, not decoration.
- Ownership is still a placeholder. A submission can conflict with event IP
  terms. Review them before uploading the repository anywhere the terms require.
- One database login in the demo is a known weakness. It is tolerable only
  because the data mode is synthetic.

## Phase 2 — Stronger financial and graph analysis

### Functional objectives

- A second, explicitly selected allocation policy (`prorata`).
- PDF statement adapter into the same canonical transaction.
- Investigator workflow for hypotheses: name similarity and other weak signals, merge and unmerge without deleting accounts.
- Further indicator codes, each with its own version: structuring-style splits, round amounts, short-dwell variants.
- Persisted graph projection only if case graphs miss the interactive latency target.

### Technical dependencies

- Phase 1 methods versioned and pinned by tests.
- A real sample of each PDF layout that will be supported. No sample, no parser.

### Deliverables

- `prorata.v1` and tests that show it diverges from FIFO on `ring-01` where the policies should diverge.
- Parser interface with one PDF implementation and a rejection path.
- Resolution decisions in the UI.
- A short profiling note if a projection table or Neo4j is proposed, matched to the trigger in ADR 0004.

### Acceptance criteria

Choosing a policy is visible on the run and the report. PDF failures do not create partial transactions. A name match cannot confirm itself. Existing `fifo.v1` hashes for unchanged inputs remain valid.

### Testing requirements

Policy comparison fixture, PDF rejection fixture, and an authorisation test that an analyst still cannot merge parties.

### Known risks

- PDF layouts vary by bank and will dominate the schedule if allowed to. Cap the number of layouts.
- Two policies will confuse a demo. The UI must show the policy name before the picture.
- Early Neo4j adoption would create a second store to keep honest. Resist it until the trigger is met.

## Phase 3 — Infrastructure history and cross-case intelligence

### Functional objectives

- RDAP, certificate-transparency, and ASN adapters on the observation model.
- Related-domain hypotheses from shared nameservers or certificates, clearly labelled.
- Historical comparison of DNS observations.
- Cross-case exact identifier work at a larger fixture size, still with the disclosure rule.

### Technical dependencies

- Phase 1 observation tables.
- A decision to enable outbound lookups, with the rate limit configured.
- Fixture data that does not require the live internet for tests.

### Deliverables

- Adapters and provenance methods for the three sources.
- A hypothesis generator that cites observation ids.
- A timeline view of observations for one domain.

### Acceptance criteria

A changed DNS answer adds a row and does not delete the previous one. A related-domain suggestion is a hypothesis. Tests pass with fake HTTP transports. Cross-case responses for an unassigned case still omit narratives.

### Testing requirements

Contract tests for the fake transports, an immutability test for observations, and an access test for cross-case infrastructure matches.

### Known risks

- Live lookups leak investigative interest to the resolver or the lookup provider. Default remains off for routine development.
- Shared hosting is common. Suggestions will be noisy. The hypothesis label is what keeps that noise from becoming a finding.

## Phase 4 — Evidence hardening and operational readiness

### Functional objectives

- Fit the system to hold official records under an explicit organisational decision.
- Separate database roles, backups, and a restore rehearsal.
- OIDC sign-in.
- Field-level audit for revealing a full account number.
- Dependency and threat-model review against the code that actually shipped.

### Technical dependencies

- A named operational owner for retention, identity, and hosting.
- Confirmation of the copyright owner and the right to process the data.
- Phase 1 triggers already in place.

### Deliverables

- Role-separated database deployment.
- Backup and a recorded restore.
- OIDC authenticator.
- Updated threat model.
- Operator runbook.

### Acceptance criteria

`vagexa_app` cannot update a transaction or delete an audit row, even without relying on application code. A restore onto a clean machine brings back a synthetic rehearsal dataset. Official mode still rejects synthetic cases. No official data is loaded as part of the acceptance test itself.

### Testing requirements

Role tests run as `vagexa_app`. A restore drill checklist is executed once and the result is written down. Regression suite from Phase 1 still passes.

### Known risks

- Institutional identity and hosting slip. The software can be ready before the organisation is. Do not fill the gap by putting official files in the demo database.
- Hardening work is easy to describe and easy to postpone. It stays a phase, not a backlog label on the hackathon branch.

## Phase 5 — Institutional integration

### Functional objectives

- Import from an authorised source when a real interface and a legal basis exist.
- A catalogue of bank-specific parsers maintained as adapters.
- Separation by district or unit if more than one unit shares a deployment.
- Retention and legal hold once the organisation sets the periods.
- A handover export a receiving unit can read without direct database access.

### Technical dependencies

- Phase 4 complete. Official mode is otherwise unsupported.
- Written interface specification from the source organisation. VAGEXA does not invent an NCRP or bank API.
- The ownership placeholder replaced, and hackathon or employment IP terms resolved.

### Deliverables

- One authorised importer, or none if no interface is provided.
- Tenancy or unit partition decided in an ADR before it is coded.
- Retention job that can delete or hold according to the written policy.
- Handover export with hashes and a manifest.

### Acceptance criteria

The importer refuses to run in `synthetic` mode against official feeds, and refuses to run in `operational` mode against generated batches. A handover manifest lists every file hash. Retention does not delete a record under hold.

### Testing requirements

Importer contract tests using a captured sample that contains no real personal data, or a synthetic sample shaped like the specification. A tenancy test proves unit A cannot read unit B.

### Known risks

- Scraping a portal would break the product's legal posture. If an interface is not provided, this phase waits.
- Multi-unit tenancy is difficult to retrofit. The ADR comes before the feature.
- Retention deletes are in tension with append-only evidence. The resolution has to be an organisational policy implemented as a privileged process, not a quiet `DELETE` in the application role.

## Immediate next task

The audit decisions H01, H03, H04, and H11 are recorded in ADR 0014. The
execution order is milestone M1 in
[Development milestones](DEVELOPMENT_MILESTONES.md): the Python package, the
React shell, Compose, and the first migration using the corrected instrument,
observation, and append-only rules, plus session login, case creation, and
the authorisation and trigger tests. The authorisation test includes an
unassigned administrator receiving 404. Leave FIFO and the graph screen until
M1 is green.
