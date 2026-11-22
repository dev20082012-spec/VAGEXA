# Phase 1 implementation blueprint

Date: 2026-11-22. This is the execution contract for the first working VAGEXA
release. It follows the architecture audit and ADRs 0001–0014. It does not
reopen them.

Field-level detail lives in the companion specifications listed at the end.
This file is the boundary, the journeys, and the consistency rules.

## Baseline

| Check | Result |
| --- | --- |
| Unresolved critical findings | None. C01–C08 are corrected in the design. |
| Owner decisions still open | None that block Phase 1. H01, H03, H04, and H11 are ADR 0014. |
| Conflict found while writing this blueprint | `PHASE_1_SCOPE.md` still said the fixture numbers were unapproved. ADR 0014 had already adopted the data-validation tables. That sentence is corrected. |
| Assertion vocabulary | The words "directly supported", "corroborated", "inferred", "hypothetical", "unresolved", and "contradicted" are mapped onto the approved three kinds in [Algorithm specifications](ALGORITHM_SPECIFICATIONS.md). A fourth `assertion_kind` is not added. ADR 0006 stands. |
| Risk scores | No risk-assessment table and no numeric culpability score. Indicators remain rule matches. |

No further approval is required before increment 1A.

## What this release is

One assigned investigator can take a synthetic case from sign-in to an
exported report: load statements, see the rows, run FIFO, read the residual,
see fan-in and fan-out on verified edges, see a shared account only as a
masked count, see two domains on one IP with the non-ownership limitation,
and run a named copilot tool that cites evidence ids.

The data source for the prototype is the synthetic fixture in
[Data validation report](DATA_VALIDATION_REPORT.md). There is no government
feed and no organiser sample file in this repository.

## Users and roles

| Role | May do without a case assignment | May do when assigned |
| --- | --- | --- |
| `administrator` | Create users, disable users, assign people to cases | Whatever the assignment role allows. The administrator role alone cannot open a case. |
| `investigator` | Create a case. The creator is assigned `lead` in the same transaction. | Upload, complain, observe, trace, confirm or reject, annotate, export |
| `analyst` | Nothing about case content | Run traces and indicators, read, use copilot tools. Cannot confirm, reject, or upload. |
| `auditor` | Nothing about case content | Read the case and its audit trail. Cannot change it. |

An unassigned user, including an unassigned administrator, receives 404 on
case routes. The body does not contain the title.

## Journeys

1. Sign in, fail to open someone else's case, open an assigned synthetic case, see the classification banner.
2. Upload a subject-identified CSV. Open a transaction and land on the file hash and line number.
3. Confirm seeds. Run `fifo.v1` at horizon 3. Read layers and the `outside_horizon` residual for the fixture's last account. Do not describe that residual as an attributed beneficiary.
4. Read `FAN_IN` and `FAN_OUT` with support transactions and the statement that narration edges were excluded.
5. Open the graph. Statement edges are visible before a trace. FIFO edges appear after the run and carry the policy version.
6. Record two domains and one shared IP. Read the overlap limitation.
7. Open the cross-case signal as a user assigned to only one case. See a masked key and a count.
8. Run `common_beneficiaries` or `trace_summary` by tool name. Read evidence ids. No model is configured.
9. Export the HTML report. It escapes narration, lists methods, and includes the non-guilt sentence.
10. An administrator creates a user and an assignment, and still cannot read the case until assigned.

## Analytical capabilities in this release

- Canonical CSV normalisation with a required subject account.
- Reprocess that appends a statement and does not update amounts.
- FIFO allocation, per-account conservation, residuals.
- Fan-in, fan-out, and pass-through on the approved rules.
- Case graph, hop cap 5, default 3, connected components named `component`.
- Manual infrastructure observations and overlap that is not ownership.
- Exact-identifier cross-case counts.
- Named copilot tools over those results.
- Append-only evidence, provenance, and audit.
- Analyst notes, stored as notes, never as findings.

## Excluded from this release

PDF parsing, pro-rata, cycle labels, centrality, community detection,
velocity scores, live DNS in the demo, RDAP, certificates, ASN, Neo4j, Redis,
an LLM, keyword routing, a guilt or mule flag, a numeric risk score, wallet
instruments, parent-domain grouping, and any official or scraped dataset.

Name-similarity merge stays out of the milestone. `parties` and
`account_party_links` exist so an investigator can record an explicit link
later in the same schema. Phase 1 does not auto-create a party from a holder
name. Two printed names remain two `account_observations`.

## Known limitations

- A victim statement that does not name the next account cannot show layer 2.
- Horizon 3 does not attribute the fourth hop.
- Date-only rows do not get an invented time, and pass-through does not apply a dwell test to them.
- Fan-in ignores inferred narration edges by decision.
- Shared IP is co-occurrence only.
- Hashes and triggers are tamper-evidence against ordinary application writes. They are not a legal certificate and not a defence against a database superuser.
- The demo database login is a single role. That is accepted only because the mode is synthetic.

## Success and acceptance

The release is successful when the ten demo steps in
[Phase 1 scope](PHASE_1_SCOPE.md) pass on a clean Compose stack in
`synthetic` mode, the conservation test uses a multi-hop fixture whose hop
sum exceeds the seed, and an unassigned administrator receives 404.

Build order is [Development milestones](DEVELOPMENT_MILESTONES.md). Do not
start the analytical modules before milestone M1 is green.

## Consistency check

| Rule | Where it is the same |
| --- | --- |
| Horizon 3, residual is not an attributed beneficiary | ADR 0014, algorithm example, graph shape 1, report copy |
| Fan-in counts verified edges only | ADR 0014, `indicators.v1`, indicator API limitation |
| Administrator must be assigned to read a case | ADR 0014, security matrix, API case GET |
| Copilot takes a tool name | ADR 0014, API body, copilot screen |
| No numeric risk score and no fourth assertion kind | This blueprint, algorithm mapping, database "tables not created" |
| Graph is not a second database | Graph spec, ADR 0004 |
| Shared IP is not ownership | ADR 0011, correlate output, infrastructure screen |
| Money is a decimal string | Database spec, API examples |

## Companion specifications

| Document | What it freezes |
| --- | --- |
| [Database implementation spec](DATABASE_IMPLEMENTATION_SPEC.md) | Tables, keys, indexes |
| [Graph implementation spec](GRAPH_IMPLEMENTATION_SPEC.md) | Derived graph and the five shapes |
| [Backend module spec](BACKEND_MODULE_SPEC.md) | One package, module duties |
| [API contracts](API_CONTRACTS.md) | Requests and responses |
| [Algorithm specifications](ALGORITHM_SPECIFICATIONS.md) | `fifo.v1`, `indicators.v1`, `correlate.v1` |
| [Evidence data contract](EVIDENCE_DATA_CONTRACT.md) | Provenance and integrity |
| [Frontend implementation spec](FRONTEND_IMPLEMENTATION_SPEC.md) | Screens |
| [Security implementation spec](SECURITY_IMPLEMENTATION_SPEC.md) | Authn, authz, prototype bar |
| [Testing and acceptance plan](TESTING_AND_ACCEPTANCE_PLAN.md) | Tests and the fixture |
| [Development milestones](DEVELOPMENT_MILESTONES.md) | The order of work |
