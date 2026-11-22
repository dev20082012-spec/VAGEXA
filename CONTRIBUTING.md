# Contributing to VAGEXA

VAGEXA is a proprietary financial-crime intelligence project. Contributions are
welcome only on the terms below. This file is a project policy. It is not a
completed legal assignment, because the copyright owner is still
`[COPYRIGHT OWNER TO BE CONFIRMED]`.

## Ownership

- Original project material is intended to be All Rights Reserved. See `LICENSE`
  and `NOTICE`.
- Do not add an MIT, Apache, GPL, or other open-source licence header.
- Do not change `LICENSE` to an open-source licence.
- A GitHub handle is not the copyright owner. Do not replace the placeholder
  with a username.
- Until a legal owner is confirmed, contributors retain whatever rights the law
  already gives them. Submitting a change does not, by itself, assign those
  rights to the placeholder.
- A future confirmed owner may require a written contributor agreement before
  accepting further work. Do not invent that agreement in a pull request.
- Before a hackathon submission or any external distribution, review the event's
  intellectual-property terms and any college or employer claim on contributor
  work. If those terms conflict with `LICENSE`, stop and resolve the conflict
  first.

## What may be committed

- Application code, tests, synthetic scenarios, and documentation that follow
  `docs/` and `.cursor/rules/`.
- Third-party material only when its licence allows the intended proprietary
  use, and only with an entry in `NOTICE`.

## What must not be committed

- Real bank statements, complaint files, exports from a police system, or any
  other operational or personal data.
- Passwords, session secrets, API keys, private keys, or `.env` files.
- Ground truth presented as if an investigator had concluded it. Ground truth
  belongs only to labelled synthetic scenarios and their tests.
- Vendored copies of libraries that should be installed as dependencies.

## Engineering rules

- Read `docs/PRODUCT_VISION.md`, `docs/EVIDENCE_AND_PROVENANCE.md`, and
  `docs/IMPLEMENTATION_ROADMAP.md` before adding a feature.
- Business rules for tracing, indicators, correlation, and evidence do not go
  in HTTP handlers or React components.
- An architectural change needs a new file in `docs/decisions/` that records
  the context, the decision, and the alternatives.
- Financial amounts use exact decimals. JSON amounts are strings.
- Every new relationship carries provenance and an assertion kind:
  `verified`, `inferred`, or `hypothesis`.
- `verified` means the claim is copied from a cited field in a source record.
  It does not mean a court has found the claim proved.
- Indicators cite the records that fired them. They are not a flag that a
  person is guilty.
- AI output may explain tool results. It may not invent entities or edges.
- Synthetic and operational records stay in separate data modes.

## Tests expected with behaviour changes

- Tracing, amount handling, classification checks, and authorisation need
  automated tests.
- A change to a matching or layering rule updates the method version and a
  fixture that states the expected result.
- Documentation-only changes do not require a test suite that does not exist
  yet. Once the suite exists, do not bypass it.

## Review standard

A change is ready when a reviewer can see where each new claim comes from, which
assertion kind it has, and which test would fail if the claim were fabricated.
