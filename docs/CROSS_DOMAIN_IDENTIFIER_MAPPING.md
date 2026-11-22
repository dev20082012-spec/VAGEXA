# Cross-domain identifier mapping

`correlate.v2` adds one rule to `correlate.v1`, shown in the first row. ADR 0017.

| Identifiers | Rule | Class | If the key is missing |
| --- | --- | --- | --- |
| Gateway record and a statement row | Same reference, amount, and currency, and the row runs from the record's payer to its payee | `gateway_merchant`, `verified` for what the record states | No proposal. The record stays listed |

These are the matches `correlate.v1` implements. Similar text is not a
match. A public resolver, a registrar, or a shared host is not ownership.

| Identifiers | Rule | Class | If the key is missing |
| --- | --- | --- | --- |
| Narration host and a domain observed in the case | Exact normalised host, including the host of a URL. The original narration is kept. | `mentioned_in`, `verified` for containment | No proposal. A domain that was never observed is not created. |
| Narration address and an IP observed in the case | Canonical IP equality | `mentioned_in`, `verified` for containment | No proposal |
| Two DNS observations, same IP, two domains | Exact address id | `infrastructure_overlap`, `verified` for co-occurrence | No proposal |
| Two hosting notes, same provider string, two addresses | Exact normalised provider string | `infrastructure_overlap`, `verified` for co-occurrence | No proposal |
| Two structured statement rows, same reference | Exact `reference_raw` | `same_payment`, `verified` | A narration-only resolution does not count |
| Account number in another case | Existing cross-case count | Signal, `inferred` | No stored cross-case row |
| Domain name in another case | Existing cross-case count | Signal, `inferred` | No title, no answers |
| Certificate fingerprint, ASN, registrar id | Not stored | Not matched | `not_collected` |
| Similar holder name | Not run | No `possible_same_party` row | Name similarity is deferred |
| Same calendar day only | Not a rule | Nothing | Time overlap is not a key |

False-positive controls: `syn-aa.test` does not match `syn-a.test`. A narration
that says "salary" on the same day as a DNS observation creates no link.
Shared hosting keeps the overlap limitation and does not create a party.
