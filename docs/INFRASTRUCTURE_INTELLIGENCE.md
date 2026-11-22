# Infrastructure intelligence

Investigators are given domains and addresses in complaints and narrations.
This engine stores those indicators and, when enabled, records passive
observations about them: DNS answers, and later registration, certificate, and
ASN data. It correlates those observations with cases. It does not discover
infrastructure by scanning the network.

## Allowed collection

| Source | When | What is stored |
| --- | --- | --- |
| Investigator entry | Always available | The name or address they typed, the case, the time, and their user id. |
| DNS resolution | `VAGEXA_PASSIVE_INTEL` is enabled | RR type, rdata, resolver identity, observation time, provenance method `dns_query`. |
| RDAP | Phase 3 adapter | Registration fields the response actually contained, retrieved time, source URL. |
| Certificate transparency | Phase 3 adapter | Names and certificate metadata returned for a name the investigator supplied. |
| ASN lookup | Phase 3 adapter | The ASN mapping returned for an IP already in the case. |

Each lookup inserts observations. It does not update older ones. The latest
answer is a query over observation time, and the screen shows that time.

## Not in this product

The following are outside every phase and every adapter, including future ones,
unless a new ADR explicitly reopens the boundary with a legal basis:

- port scanning, service fingerprinting, and vulnerability probing;
- exploitation, credential attacks, and traffic interception;
- collection against systems the investigator did not identify;
- presenting a registrar or hosting field as the identity of a suspect.

Passive lookup can still affect a third party's logs. The deployment notes that,
and the default is off.

## Model

Domains and IP addresses are global instrument rows, like accounts: one row per
normalised name or address, shared so cross-case exact matches are possible.
The sensitive material is the link to a case, which is a `relationships` row or
a case-scoped hosting note, and is authorised like other case data.

Normalisation:

- domains: trim, lowercase, remove a trailing dot, reject spaces;
- IP addresses: PostgreSQL `inet`, so `192.168.001.002` is not a different key from its canonical form.

A URL in a complaint is reduced to a host for matching only by a versioned
parser. The original URL string remains in the complaint or the note. The
parser does not fetch the URL.

## Assertion kinds

| Claim | Kind |
| --- | --- |
| "This complaint text contains this domain string." | `verified` if the stored narrative contains that exact host. Otherwise not asserted. |
| "This resolver returned this address at this time." | `verified` against the DNS observation. |
| "This domain is related to this fraud because it shares a nameserver with another domain." | `hypothesis` until an investigator confirms the investigative relevance. The shared nameserver itself can be `verified` as an observation. |
| "This IP is the offender's server." | Not a claim the system is allowed to store. |

Related-domain suggestions from shared nameservers, shared certificates, or
successive addresses are Phase 3. They are hypotheses with the observation ids
attached. They are not automatically added to the case as infrastructure the
suspect "uses".

A shared IP, nameserver, or provider string is an overlap. The verified claim
is that the observations contain the same key. It is not common ownership,
common control, or a common operator. The limitation is stored on the row and
shown next to the edge. ADR 0011.

## History

Infrastructure changes. The engine keeps history by append-only observations.
A report that says "resolved to 203.0.113.10" must include the observation id
and time. A later answer of a different address does not delete the first.

Missing history is a gap, not a negative proof. "No DNS observation is stored"
does not mean "the domain does not resolve".

## Correlation into the case

The correlation engine consumes identifiers. This engine's job is to produce
clean observations and to avoid turning a lookup into an accusation. Shared
domain name across cases uses the identifier path in
[Correlation engine](CORRELATION_ENGINE.md). A shared IP uses the overlap
rule in that document, which does not assert common ownership.

## Failure and abuse limits

- Lookup timeouts become a failed job or a failed observation attempt with an error code, not an empty observation that looks like "no records".
- The worker rate-limits outbound lookups per deployment. The first limit is a configuration value, defaulting to a low fixed rate, so a large paste of names cannot become an open resolver flood.
- Names are those already stored on the case. The adapter does not accept an arbitrary internet-wide suffix search.

## First-slice cut

Phase 1 stores manual observations and one DNS A/AAAA lookup adapter behind the
port, disabled by default. The demonstration scenario includes a planted domain
and address as investigator-supplied observations so the correlation tests do
not depend on live DNS. Live lookup is tested with a fake resolver.
