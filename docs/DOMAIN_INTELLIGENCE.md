# Domain intelligence

A domain is the normalised name, not a registrant and not a suspect.

Normalisation, version `observe.v1`:

- trim and lowercase;
- remove one trailing dot;
- encode internationalised labels with IDNA;
- reject spaces, empty names, URLs, and empty labels.

`Syn-A.TEST.` and `syn-a.test` are one row. `bücher.example` is stored as
`xn--bcher-kva.example`. `syn a.test` is rejected.

Subdomains are ordinary names. `a.syn-a.test` does not automatically become a
child of `syn-a.test`, and the two are not merged.

This release does not store registrar, registration dates, expiration,
nameserver records, or domain status. Those fields are Phase 3 RDAP
observations. A nameserver string an investigator types is a hosting-note
provider string, not an NS lookup.

The same normalised name in another case is a count on the cross-case signal.
The other case's title and its answers are not returned.
