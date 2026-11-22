# Correlation engine

Correlation proposes relationships between records the system already holds.
It does not create the records. Financial facts come from statements.
Infrastructure facts come from observations. A correlation row is either a
direct reading of those facts or a named inference, and it always points back
to them.

## Inputs

- accounts and the identifiers on transactions;
- complaints and the identifiers extracted from them;
- domain, DNS, IP, and hosting observations;
- trace flows, as derived inputs, which may support an inferred flow and never
  replace the source transaction.

## Outputs

Rows in `relationships` plus, when a human-readable conclusion is stored, a
`findings` row whose support lists the evidence ids. Proposed rows have status
`proposed`. An investigator confirms or rejects them. Rejection remains stored.

Confirmation means "an investigator accepts this as a working link". It does
not change `assertion_kind`. `verified` is reserved for a source field, or for
a co-occurrence that the observations literally contain, and the claim text
must be no wider than that field. An overlap row is not confirmed into an
ownership finding. ADR 0011.

## Link catalogue for the first method `correlate.v1`

| Signal | Kind | Assertion | Auto status |
| --- | --- | --- | --- |
| Same account number and IFSC on two transactions or complaints | `shared_account` | `inferred` | `proposed` |
| Same VPA | `shared_vpa` | `inferred` | `proposed` |
| Same UTR on two legs | `same_payment` | `verified` when both references are structured fields | `proposed` for human acknowledgement, without weakening the assertion |
| Domain string exactly present in a stored narrative | `mentioned_in` | `verified` | `proposed` |
| DNS observation for that domain | `resolves_to` | `verified` | recorded as an observation edge, not a suspicion |
| Same IP, nameserver, or hosting-provider string on two observations | `infrastructure_overlap` | `verified` for co-occurrence only | Shown with a mandatory limitation: shared hosting, DNS, or an address does not establish common ownership, common control, or a common operator. No party is created. |
| Same domain name recorded in two cases | `shared_domain_name` | `inferred` as "the same name was recorded" | Limitation: not proof of common control or of who registered the name |
| Similar holder name | `possible_same_party` | `hypothesis` | `proposed` and never auto-confirmed |

Absence of a signal is not a relationship of type "unrelated". The engine says
nothing in that case.

## Cross-case access

Exact identifier matches are useful and easy to over-disclose.

- The caller always receives, for their own case, the local identifier and the count of other cases that contain it.
- Identifiers in that payload are masked the same way as in the UI.
- Titles, narratives, complainant text, and transaction rows from another case are included only when the caller is assigned to that case or has the cross-case read permission.
- The lookup writes audit action `cross_case.lookup`.

A demonstration user in the synthetic deployment is assigned to every synthetic case so the shared-beneficiary story is visible. That assignment is fixture data, not a weakening of the check.

## Financial and digital joins

The join key between money and infrastructure is an identifier present in both, in this order:

1. a domain or URL host extracted by the versioned extractor from a narration or complaint;
2. an IP explicitly present in a note or, rarely, a narration;
3. a shared identifier already accepted inside the case.

The engine does not join "suspicious amount" to "newly registered domain" by score. Those can be two indicators on the same case. A relationship requires a key.

## Provenance

Each proposed relationship stores `method_name=correlate.v1`, the signal name, and a provenance record whose `source_reference` lists the input ids. A finding that says "these two complaints share a beneficiary" must list both account evidence ids. If one of them is missing, the finding is not written.

Derived trace flows may be cited to explain a layer. They are classified `derived` and do not count as a second independent source.

## Conflicts

If two methods disagree, both proposals can exist. The engine does not delete the weaker one. The investigator rejects the one they will not use. The report lists open proposals separately from confirmed ones so a rejected or undecided link is not printed as a fact.

## What correlation must not do

- Mix a synthetic case with an official case in one relationship. The use case checks both classifications and refuses.
- Upgrade assertion kind because a model sounded confident.
- Create a party row from a name match.
- Pull in related domains that no observation in the case supports yet. That suggestion is a Phase 3 hypothesis from the digital engine, still confirmed by a person before it is treated as case infrastructure.
