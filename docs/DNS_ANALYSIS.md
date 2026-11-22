# DNS analysis

Phase 1 stores investigator-supplied A and AAAA answers. MX, NS, CNAME, and
TXT are not stored. A request for another type is 422.

Each row has the normalised name, the record type, the canonical address, the
observation time, the resolver label, the provenance id, and the case. The
resolver for a typed answer is `investigator_entry`. A test double may write
`fake_resolver`. Nothing in this release writes `dns_query`, because no
resolver runs.

Observations are append-only. Two different addresses for one name at two
times are both returned. The later row does not delete the earlier row.
"No observation is stored" does not mean the name does not resolve.

A `resolves_to` graph edge cites that observation id, the provenance id, and
the observation time. The assertion is `verified` against the stored answer.
It is not a claim that the address is still current, and it is not a precise
place.
