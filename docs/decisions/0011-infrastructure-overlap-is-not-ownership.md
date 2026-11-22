# 0011. Infrastructure overlap is not ownership

- Status: accepted
- Date: 2026-11-22

## Context

The correlation catalogue stored a shared IP, shared hosting provider, or
shared DNS infrastructure as `shared_infrastructure` with assertion kind
`inferred`. That kind means a method derived a claim from verified inputs.
Readers will treat the claim as "these cases are connected". Shared addresses
and shared resolvers are common for unrelated customers. The audit's rule is
that those facts must not automatically establish common ownership, common
control, or criminal attribution.

An exact host string inside a complaint is a different fact. It is evidence
that the text contains the host. It is still not evidence that the registrant
committed the fraud.

## Decision

Co-occurrence of an IP address, nameserver, or hosting-provider string is
stored as overlap. The assertion kind is `verified` only for the sentence
"these observations contain the same key". The row carries a limitation that
common ownership, common control, and a common operator are not established.
The system does not create a party from the overlap and does not confirm the
overlap into a stronger kind.

An exact domain name shared across cases is an identifier co-occurrence. It
may be `inferred` as "the same name was recorded", with the same limitation
on ownership. It is not a registrant finding.

`mentioned_in` for a host that is literally in stored text is `verified` for
containment only.

## Consequences

- The old `shared_infrastructure` inference is not an allowed write.
- Scenario 5 in the data validation report is the acceptance example.
- Later RDAP or certificate fields stay observations. A registrant name does
  not auto-merge a party.

## Alternatives

- Keep `inferred` and rely on analysts to discount it. The graph would still
  draw a connection that the method overclaims. Rejected.
- Drop infrastructure links entirely. The investigator would not see a real
  co-occurrence. Rejected. The overlap is shown, and the claim is narrowed.
