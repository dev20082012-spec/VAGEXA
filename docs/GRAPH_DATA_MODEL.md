# Graph data model

The investigation graph is a view over relational facts. Nodes and edges are
derived, bounded by a case and a hop limit, and stamped with an assertion kind.
[ADR 0004](decisions/0004-derived-graph-networkx.md) explains why this view is
built with NetworkX in the first releases and how a graph database would be
added later without becoming the system of record.

## Node kinds

| Kind | Source | Identity |
| --- | --- | --- |
| `account` | `accounts` | Account UUID. Label is a masked number or VPA unless the caller reveals it. |
| `party` | `parties` | Party UUID. Present only when a party row exists. |
| `complaint` | `complaints` | Complaint UUID. |
| `domain` | `domain_names` | Domain UUID. |
| `ip` | `ip_addresses` | IP UUID. |
| `autonomous_system` | `autonomous_systems` | ASN UUID. |
| `cash_exit` | A cash debit with no destination | Synthetic node id scoped to the trace flow. Not an account. |

A cash exit exists so the drawing can end honestly. It is not a person and not
a beneficiary.

## Edge kinds

| Kind | Meaning | Usual assertion |
| --- | --- | --- |
| `transfer` | Value moved from one account toward another, or toward a cash exit, inside a trace run or a source transaction. | `verified` when a statement field names both sides. `inferred` when FIFO or an unambiguous narration pattern produced it. |
| `named_in` | A complaint text or structured field mentions an account or domain. | `verified` for a structured field. `hypothesis` for a string found in free text until confirmed. |
| `resolves_to` | A DNS observation maps a domain to an address at a time. | `verified` against that observation. It is not a permanent fact about the domain. |
| `announced_by` | An IP is recorded in an ASN observation. | `verified` against that observation. |
| `hosted_with` | A hosting note ties an address or domain to a provider string. | Matches the note's provenance. Manual notes start as `unverified` classification and `hypothesis` until their source is stronger. |
| `same_as` | An investigator merged two records. | The decision's assertion. Not inferred from a similar name. |
| `shared_with_case` | A cross-case signal edge shown only to a caller who may see both cases. | `inferred` for an exact identifier match. |

Every edge payload includes:

- `assertion_kind`: `verified`, `inferred`, or `hypothesis`;
- `method_name` and `method_version`;
- `evidence_ids` or a `provenance_id`;
- for money edges, `amount` as a decimal string, `currency`, and `trace_run_id` when the edge comes from allocation;
- `observed_at` or `valid_from` / `valid_to` when the fact is temporal.

Edges of different assertion kinds between the same pair are kept as separate
edges. Collapsing them would hide whether the picture is a statement or a guess.

Stored `relationships.rel_type` values use the correlation catalogue
(`shared_account`, `shared_vpa`, `same_payment`, `mentioned_in`,
`infrastructure_overlap`, `shared_domain_name`, `possible_same_party`,
`same_as`). The graph view maps them onto the edge kinds above.
`mentioned_in` is shown as `named_in`. `infrastructure_overlap` is shown as
`resolves_to` or `hosted_with` with the non-ownership limitation on the edge.
`shared_account` and `shared_vpa` are shown as `transfer` only when a money
movement exists; otherwise they are a non-money edge labelled with the stored
type. `shared_with_case` is a view-only edge and is not a stored type.

## What is not a node

Transactions are evidence on edges, not nodes, in the case graph the
investigator first sees. A transaction inspector lists the rows for a selected
edge. Promoting every transaction to a node makes fan-in unreadable and is
deferred until a concrete screen needs it.

Holder names, phone numbers, and free-text remarks are attributes or
hypotheses. They are not nodes merely because they were parsed.

## Build steps

For a request `(case_id, focus, max_hops)`:

1. Authorise the case.
2. Refuse `max_hops` greater than 5. Default is 3.
3. Load accounts cited by the case, statement-backed counterparty edges, trace flows for the selected run if one exists, complaints, and infrastructure observations. Do not load other cases' narratives. Statement-backed edges are drawn even when no trace has been run. FIFO edges carry `trace_run_id` and are not a second copy of the statement edge unless the amounts or the assertion kinds differ, in which case both are kept.
4. Build a directed NetworkX multigraph in memory.
5. If `focus` is set, keep nodes within `max_hops` of the focus in the undirected sense for neighbourhood display, and keep transfer direction on the edges.
6. Optionally compute weakly connected components on that subgraph and return them as `component_id`. The field name is `component`. It is not `gang`, `network`, or `community` in the first release.
7. Set `truncated: true` when nodes were dropped because of the hop bound.
8. Discard the in-memory graph at the end of the request.

Path search uses `cutoff=max_hops`. The API does not expose an all-paths query
without a source, a target, and a cutoff.

## Temporal behaviour

DNS and hosting edges carry the observation time. The graph response for "what
did we know" uses the observations available at request time and lists those
times. The product does not rewrite an old observation when a new lookup
differs. Historical comparison is the set of observations, not a mutable
"current IP" cell.

Transfer edges carry the booking date of the source transaction. A trace that
is rerun after new statements are ingested is a new `analytical_run`. Old runs
remain.

## Entity resolution

Resolution is conservative and ordered:

1. Exact `(account_number_norm, ifsc_norm)` or exact `vpa_norm` reuses one account row. This is identity of the instrument as printed, not identity of a human.
2. Exact UTR / RRN equality can link two statement rows about the same payment when both sides are present. That link is `inferred` unless both rows are structured fields from source files, in which case the match method is `reference_join` and the assertion is `verified` against those two fields.
3. Similar holder names create a proposed `hypothesis` relationship at most. They never share an account row.
4. A human merge writes `resolution_decisions` and a `same_as` edge. Unmerge is a later decision. Accounts are not deleted.

No probabilistic merge runs unattended in the first release.

## Cross-case graph

Shared exact identifiers are computed by a query across accounts and domains.
The result for an unprivileged caller is a signal list: kind, redacted
identifier, other-case count, assertion kind `inferred`, method
`exact_identifier`. It is not a set of foreign nodes with titles.

When the caller is assigned to both cases, the UI may show a `shared_with_case`
edge. Opening the other case is a normal authorised read and is audited.

## Neo4j mapping, later and conditional

If [ADR 0004](decisions/0004-derived-graph-networkx.md) triggers are met, the
projection is:

| Relational source | Graph label |
| --- | --- |
| `accounts.id` | `:Account {id}` |
| `domain_names.id` | `:Domain {id}` |
| `ip_addresses.id` | `:Ip {id}` |
| `trace_flows` and verified counterparty links | `:TRANSFER` |
| `dns_observations` | `:RESOLVES_TO` |
| `relationships` | relationship type matching `rel_type` |

Properties required on every projected relationship: `assertion_kind`,
`method_version`, `provenance_id`, `projected_at`. The projection job can drop
and reload. Investigators do not edit the graph database. Cypher lives in the
adapter. User text and model text are not Cypher.

## Invariants the graph service must hold

- No edge without provenance.
- No hop beyond the requested cap.
- No node whose case the caller cannot read, except the redacted cross-case signal shape.
- No mutation of PostgreSQL facts while laying out a picture.
- Repeating the same request against the same committed runs returns the same nodes and edges. Layout coordinates may differ and are not evidence.
