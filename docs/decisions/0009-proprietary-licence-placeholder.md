# 0009. Proprietary licence with an unconfirmed owner

- Status: accepted
- Date: 2026-11-22

## Context

VAGEXA is intended as proprietary software for long-term investigative use.
The legal owner has not been confirmed to the project. The git remote uses the
GitHub handle `dev20082012-spec`. A handle is not a legal person or entity, so
it must not be written into the copyright line as if it were.

An open-source licence would contradict the stated intention and is harder to
undo once others have relied on it. Hackathon terms and college rules may also
claim rights in participant work. Those documents were not available as
attachments to this decision.

## Decision

`LICENSE` is an All Rights Reserved notice with the owner set to
`[COPYRIGHT OWNER TO BE CONFIRMED]`. `NOTICE` records third-party material and
currently lists none. `CONTRIBUTING.md` tells contributors that submission does
not assign rights to the placeholder.

No MIT, Apache, GPL, or other open-source licence applies to original project
material.

Before a public release or a hackathon submission, a person responsible for the
team must:

- replace the placeholder with a legal owner, or record why the submission
  cannot wait and what risk that creates;
- read the event intellectual-property terms and any contributor or college
  agreement;
- confirm the repository visibility matches the proprietary intention.

## Consequences

- The repository can proceed with engineering work without pretending the owner
  is known.
- The notice does not grant rights to third parties and does not claim their work.
- A later owner change is an update to `LICENSE`, `NOTICE`, the README, and a
  new ADR that supersedes this one. This file stays as the record of the
  placeholder.

## Alternatives

- License the project under MIT or Apache now and relicense later. Rejected.
  Downstream users could rely on the grant.
- Name a person from the git config without written confirmation. Rejected.
  That would invent an owner.
