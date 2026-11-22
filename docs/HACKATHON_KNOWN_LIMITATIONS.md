# Known limitations

These are the limits of the demonstration that was verified on
2026-11-22. They are not hidden defects in the path a judge follows.

## Working in the public MVP

- Sign-in, the `SYN-DEMO` overview, transactions, search, the outgoing
  filter, account totals, the three-hop `fifo.v1` trace, fan-in and fan-out,
  DNS and hosting observations, corroborated and contradicted gateway links,
  unresolved infrastructure overlap, the network graph, evidence records, and
  the report.
- The records are synthetic and labelled as such.
- A shared address is not described as common ownership.
- The trace does not call `****0019` the beneficiary. That account remains on
  the statement list only.

## Synthetic, not operational

- One Fly machine in Singapore, with PostgreSQL on a single encrypted volume.
- The machine is left running for the submission window. Fly does not promise
  uninterrupted uptime. Stopping it with `flyctl scale count 0 --app vagexa-rj-demo`
  keeps the volume.
- Statement clocks have no time zone and are not converted. Gateway and DNS
  times are UTC. The interface says so on the evidence record.
- There is no live DNS, certificate, RDAP, ASN, or geolocation lookup.
- There is no copilot and no model.
- Logout was visible and was not clicked in this release check.
- A separate click on a graph node, as distinct from the already selected
  gateway edge, was not repeated.

## Not built, and not part of the demonstration

- A second investigation story.
- Centrality, community detection, or a risk score.
- Public registration inside VAGEXA, email reset, or extra roles beyond the
  seeded investigator.
- An official-record deployment. Operational mode is a different database and
  is not this host.

## Submission materials that are still outside the application

The public event site asks for an action-plan PPT and a wireframe in addition
to a prototype. Those files are not in this repository. The live URL is the
prototype. Team registration on the organiser's portal was not visible from
this workspace.
