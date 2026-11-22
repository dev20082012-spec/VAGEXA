# Certificate intelligence

Certificates are not collected in this release. There is no certificate table,
no fingerprint, no issuer, and no subject-alternative-name observation.

`POST /api/v1/cases/{case_id}/observations` with `kind` `certificate` returns
422. The observation list returns `certificate_reason: not_collected`.

Certificate transparency is a Phase 3 adapter. If it is added later, a reused
certificate is a technical observation. It does not establish common
ownership. That limitation is already the overlap sentence in ADR 0011. This
release does not invent certificate edges to stand in for the missing source.
